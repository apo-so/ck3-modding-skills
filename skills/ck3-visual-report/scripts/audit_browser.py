#!/usr/bin/env python3
"""Audit supplied CK3 report files in a real browser (file://), without editing them.

Usage: python scripts/audit_browser.py report.html [other.html ...] --output qa/run
Requires Playwright and a Chromium browser. --browser may name a local executable.
Exit codes: 0 PASS; 1 observed report failure; 2 incomplete/NOT_RUN or harness error.
PASS covers this browser contract only, not research semantics or game execution.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys

VIEWPORTS = ((1440, 1000), (390, 844), (320, 760))
CARD_GROUPS = ("search", "filters", "recommended", "sort", "expand_collapse")
EXTERNAL_SCHEMES = ("http://", "https://", "ws://", "wss://")

# Keep dimensions and offending element samples: a failed width must be diagnosable.
# Rectangles inside a deliberate horizontal scroller (e.g. mobile chapter navigation)
# are excluded from offender samples; page scrollWidth itself is never suppressed.
LAYOUT_JS = """() => {
  const width = innerWidth;
  const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const clipped = e => {for(let p=e.parentElement;p&&p!==document.body;p=p.parentElement){
    const s=getComputedStyle(p);if(['auto','scroll','hidden','clip'].includes(s.overflowX)
      && p.getBoundingClientRect().right <= width+1)return true;}return false;};
  const offenders = [...document.body.querySelectorAll('*')].filter(e => {
    if(!visible(e)||clipped(e))return false;const r=e.getBoundingClientRect();
    return r.right>width+1||r.left < -1;
  }).map(e => {const r=e.getBoundingClientRect();return {
    tag:e.tagName.toLowerCase(),id:e.id,class:e.className?.toString(),
    section:e.closest('[data-section]')?.id||null,left:r.left,right:r.right,
    width:r.width,scroll_width:e.scrollWidth,client_width:e.clientWidth,
    text:e.textContent.replace(/\\s+/g,' ').trim().slice(0,180)
  };}).slice(0,20);
  return {viewport_width:width,document_scroll_width:document.documentElement.scrollWidth,
    body_scroll_width:document.body.scrollWidth,offenders};
}"""

SNAPSHOT_JS = """() => ({
  focus:document.body.classList.contains('focus-mode'),
  mode_buttons:[...document.querySelectorAll('[data-mode]')].map(e=>[e.dataset.mode,e.getAttribute('aria-pressed')]),
  mode_label:document.querySelector('#modeLabel')?.textContent,
  details:[...document.querySelectorAll('details')].map((e,i)=>({id:e.id,index:i,open:e.open})),
  cards:[...document.querySelectorAll('.case-card')].map(e=>({id:e.id,hidden:e.hidden})),
  controls:[...document.querySelectorAll('[data-search],[data-filter],[data-sort],[data-recommended]')]
    .map(e=>({value:e.value,checked:e.checked??null}))
})"""


def add_check(result, name, condition=None, detail=None, status=None):
    state = status or ("PASS" if condition else "FAIL")
    result["checks"].append({"name": name, "status": state,
                             "passed": True if state == "PASS" else False if state == "FAIL" else None,
                             "detail": detail})


def finalize(result):
    """NA cannot manufacture PASS; unavailable execution is distinct from report FAIL."""
    counts = Counter(item["status"] for item in result.get("checks", []))
    result["counts"] = {key: counts[key] for key in ("PASS", "FAIL", "NA", "NOT_RUN", "ERROR")}
    if counts["FAIL"]:
        status = "FAIL"
    elif counts["ERROR"]:
        status = "ERROR"
    elif counts["NOT_RUN"] or not counts["PASS"]:
        status = "NOT_RUN"
    else:
        status = "PASS"
    result["status"] = status
    result["passed"] = True if status == "PASS" else False if status == "FAIL" else None
    return result


def exit_code(result):
    return 0 if result["status"] == "PASS" else 1 if result["status"] == "FAIL" else 2


def default_executable():
    for command in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        found = shutil.which(command)
        if found:
            return found
    # An explicit --browser always takes precedence; otherwise try common Windows paths.
    for candidate in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                      r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if Path(candidate).is_file():
            return candidate
    return None  # Playwright's configured Chromium installation, if present.


def monitor(context, page, result, label):
    page.on("pageerror", lambda err: result["page_errors"].append({"context": label, "error": str(err)}))
    page.on("websocket", lambda ws: result["external_requests"].append({"context": label, "url": ws.url}))

    def route_request(route):
        url = route.request.url
        if url.lower().startswith(EXTERNAL_SCHEMES):
            result["external_requests"].append({"context": label, "url": url})
            route.abort()  # Record the attempt without fetching remote content.
        else:
            route.continue_()

    context.route("**/*", route_request)


def go(page, path):
    page.goto(path.as_uri(), wait_until="load", timeout=20000)


def screenshot(page, out, result, label):
    target = out / f'{result["artifact_prefix"]}_{label}.png'
    page.screenshot(path=str(target), full_page=False, animations="disabled")
    result["screenshots"].append(target.name)


def layout_check(page, result, name):
    page.evaluate("scrollTo(0,0)")
    dimensions = page.evaluate(LAYOUT_JS)
    add_check(result, name, dimensions["document_scroll_width"] <= dimensions["viewport_width"] + 1,
              dimensions)


def mode(page, name):
    button = page.locator(f'[data-mode="{name}"]')
    if button.count():
        button.first.click()
        return True
    return False


def section_visibility(page):
    return page.locator("[data-section]").evaluate_all(
        "es=>({count:es.length,hidden:es.filter(e=>!e.getClientRects().length||getComputedStyle(e).visibility==='hidden').map(e=>e.id)})")


def check_layouts_legacy(page, path, out, result):
    for width, height in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        go(page, path)
        for reading_mode in ("focus", "full"):
            label = f"{width}_{reading_mode}"
            if not mode(page, reading_mode):
                add_check(result, f"layout.{label}", status="NA", detail="This report has no matching reading-mode control.")
                continue
            focus = page.locator("body").evaluate("e=>e.classList.contains('focus-mode')")
            add_check(result, f"mode.{label}", focus == (reading_mode == "focus"))
            if reading_mode == "full":
                visibility = section_visibility(page)
                add_check(result, f"sections.{label}", bool(visibility["count"]) and not visibility["hidden"], visibility)
            layout_check(page, result, f"layout.{label}")
            screenshot(page, out, result, label)
        expand = page.locator("[data-expand]")
        if page.locator(".case-card").count() and expand.count():
            for button in expand.all():
                button.click()
            layout_check(page, result, f"layout.{width}_full_cards_expanded")
            screenshot(page, out, result, f"{width}_full_cards_expanded")
        else:
            add_check(result, f"layout.{width}_full_cards_expanded", status="NA", detail="No cards or expand control.")
    page.set_viewport_size({"width": 1440, "height": 1000})
    go(page, path)



def continuous(page):
    return page.locator('meta[name="reading-layout"][content="continuous"]').count() > 0


def open_details(page):
    page.locator('[data-local-detail]').evaluate_all('es=>es.forEach(e=>e.open=true)')


def check_layouts(page, path, out, result):
    if not continuous(page):
        return check_layouts_legacy(page,path,out,result)
    for width,height in VIEWPORTS:
        page.set_viewport_size({'width':width,'height':height});go(page,path)
        add_check(result,f'reading.{width}.no_global_mode',page.locator('[data-mode]').count()==0)
        layout_check(page,result,f'layout.{width}.continuous');screenshot(page,out,result,f'{width}_continuous')
        local=page.locator('[data-local-detail]')
        if local.count():
            summary=local.first.locator(':scope > summary');summary.scroll_into_view_if_needed()
            before=summary.bounding_box()['y'];others=local.evaluate_all('es=>es.map(e=>e.open)')
            summary.click();after=summary.bounding_box()['y'];states=local.evaluate_all('es=>es.map(e=>e.open)')
            add_check(result,f'reading.{width}.local_expansion',states[0] and states[1:]==others[1:] and abs(after-before)<=3,{'before_y':before,'after_y':after})
        open_details(page);layout_check(page,result,f'layout.{width}.details_expanded');screenshot(page,out,result,f'{width}_details_expanded')
    page.set_viewport_size({'width':1440,'height':1000});go(page,path)


def check_navigation_legacy(page, result):
    if not mode(page, "focus"):
        add_check(result, "navigation.hidden_section", status="NA", detail="No focus-mode control.")
        return
    href = page.locator('.sidebar a[href^="#"]').evaluate_all("""es=>es.map(e=>e.getAttribute('href')).find(h=>{
      const target=document.getElementById(h.slice(1));return target&&target.closest('.research-layer')&&!target.getClientRects().length;
    })||null""")
    if href is None:
        add_check(result, "navigation.hidden_section", status="NA", detail="No navigation link to a hidden research section.")
        return
    # Select by the actual href without interpolating arbitrary identifiers into CSS.
    for candidate in page.locator('.sidebar a[href^="#"]').all():
        if candidate.get_attribute("href") == href:
            candidate.click()
            break
    observed = page.evaluate("id=>{const e=document.getElementById(id);return {id,visible:!!e?.getClientRects().length,focus:document.body.classList.contains('focus-mode')}}", href[1:])
    add_check(result, "navigation.hidden_section", observed["visible"] and not observed["focus"], observed)



def check_navigation(page, result):
    if not continuous(page):
        return check_navigation_legacy(page,result)
    candidates=page.locator('.source-ref')
    link=next((x for x in candidates.all() if x.is_visible()),None)
    if link is None:
        add_check(result,'navigation.source_return',status='NA',detail='No visible source reference in this artifact.');return
    link.scroll_into_view_if_needed();y=link.bounding_box()['y'];href=link.get_attribute('href');link.click()
    target=page.locator(href)
    add_check(result,'navigation.source_revealed',target.is_visible())
    button=page.locator('[data-reading-return]');add_check(result,'navigation.return_available',button.is_visible());button.click()
    add_check(result,'navigation.return_anchor',abs(link.bounding_box()['y']-y)<=3,{'before':y,'after':link.bounding_box()['y']})


def visible_ids(cards):
    return cards.evaluate_all("es=>es.filter(e=>!e.hidden).map(e=>e.id)")


def check_card_browser(box, result, number):
    prefix = f"browser.{number}"
    cards = box.locator(".case-card")
    total = cards.count()
    if not total:
        for group in CARD_GROUPS:
            add_check(result, f"{prefix}.{group}", status="NA", detail="This browser contains zero cards.")
        return
    expected_total = box.get_attribute("data-expected-count")
    if expected_total is not None:
        add_check(result, f"{prefix}.declared_count", expected_total == str(total), {"declared": expected_total, "actual": total})
    baseline_ids = cards.evaluate_all("es=>es.map(e=>e.id)")
    add_check(result, f"{prefix}.initial_count", len(visible_ids(cards)) == total, {"actual_cards": total})
    reset = box.locator("[data-reset-filter]")
    search = box.locator("[data-search]")

    def clear():
        if reset.count():
            reset.click()
        elif search.count():
            search.fill("")

    if search.count():
        term = "CK3_AUDIT_NO_MATCH_93ba2e26"
        while any(term in text for text in cards.all_text_contents()):
            term += "_X"
        search.fill(term)
        add_check(result, f"{prefix}.search.zero", not visible_ids(cards))
        count_label = box.locator("[data-count]")
        empty = box.locator("[data-empty]")
        if count_label.count() and empty.count():
            add_check(result, f"{prefix}.search.zero_feedback", count_label.inner_text().strip() == "0" and empty.is_visible())
        else:
            add_check(result, f"{prefix}.search.zero_feedback", status="NA", detail="No count/empty-result feedback component.")
        search.fill("")
        add_check(result, f"{prefix}.search.clear", set(visible_ids(cards)) == set(baseline_ids))
        title = cards.first.get_attribute("data-title") or cards.first.locator("summary").inner_text().strip()
        if title:
            expected = cards.evaluate_all("(es,t)=>es.filter(e=>e.textContent.normalize('NFKC').toLocaleLowerCase().includes(t.normalize('NFKC').trim().toLocaleLowerCase())).map(e=>e.id)", title)
            search.fill(title)
            add_check(result, f"{prefix}.search.hit", bool(expected) and set(visible_ids(cards)) == set(expected), {"term": title, "expected": expected, "actual": visible_ids(cards)})
        if reset.count():
            clear()
            add_check(result, f"{prefix}.search.reset", set(visible_ids(cards)) == set(baseline_ids) and search.input_value() == "")
        else:
            add_check(result, f"{prefix}.search.reset", status="NA", detail="No reset control.")
            clear()
    else:
        add_check(result, f"{prefix}.search", status="NA", detail="No search control.")

    filters = box.locator("select[data-filter]")
    if not filters.count():
        add_check(result, f"{prefix}.filters", status="NA", detail="No filter controls.")
    for select in filters.all():
        field = select.get_attribute("data-filter")
        attribute = "data-" + field.replace("_", "-")
        values = select.locator("option").evaluate_all("es=>es.filter(e=>e.value&&!e.disabled).map(e=>e.value)")
        if not values:
            add_check(result, f"{prefix}.filter.{field}", status="NA", detail="No populated filter values.")
        for value in values:
            clear()
            expected = cards.evaluate_all("(es,a)=>es.filter(e=>e.getAttribute(a[0])===a[1]).map(e=>e.id)", [attribute, value])
            select.select_option(value)
            observed = visible_ids(cards)
            add_check(result, f"{prefix}.filter.{field}.{value}", bool(expected) and set(observed) == set(expected), {"expected": expected, "actual": observed})
        select.select_option("") if select.locator('option[value=""]').count() else None
        clear()

    recommended = box.locator("input[data-recommended]")
    if recommended.count():
        clear()
        recommended.check()
        expected = cards.evaluate_all("es=>es.filter(e=>e.dataset.recommended==='true').map(e=>e.id)")
        add_check(result, f"{prefix}.recommended", set(visible_ids(cards)) == set(expected), {"expected": expected, "actual": visible_ids(cards)})
        recommended.uncheck()
    else:
        add_check(result, f"{prefix}.recommended", status="NA", detail="No recommended-only control.")

    clear()
    sorter = box.locator("select[data-sort]")
    if not sorter.count():
        add_check(result, f"{prefix}.sort", status="NA", detail="No sort control.")
    else:
        values = sorter.locator("option").evaluate_all("es=>es.filter(e=>!e.disabled).map(e=>e.value)")
        records = cards.evaluate_all("es=>es.map(e=>({id:e.id,title:e.dataset.title,weight:e.dataset.weight,order:Number(e.dataset.order)})).sort((a,b)=>a.order-b.order)")
        for value in values:
            if value not in ("original", "title", "weight"):
                add_check(result, f"{prefix}.sort.{value}", status="NOT_RUN", detail="Sort contract is unknown; add a specific verifier.")
                continue
            expected = box.evaluate("""(_,args)=>[...args.records].sort((a,b)=>{
              if(args.key==='title')return a.title.localeCompare(b.title,'zh-CN');
              if(args.key==='weight'){const number=e=>e.weight?.trim()&&Number.isFinite(Number(e.weight))?Number(e.weight):-Infinity;
                const x=number(a),y=number(b);if(x!==y)return y>x?1:-1;}
              return a.order-b.order;
            }).map(e=>e.id)""", {"records": records, "key": value})
            sorter.select_option(value)
            actual = cards.evaluate_all("es=>es.map(e=>e.id)")
            detail = {"expected": expected, "actual": actual, "actual_weights": cards.evaluate_all("es=>es.map(e=>e.dataset.weight)"), "card_count": total}
            if total < 2:
                add_check(result, f"{prefix}.sort.{value}", status="NA", detail={**detail, "reason": "Only one card; reordering cannot be demonstrated."})
            else:
                add_check(result, f"{prefix}.sort.{value}", actual == expected, detail)
    clear()
    expand, collapse = box.locator("[data-expand]"), box.locator("[data-collapse]")
    if expand.count() and collapse.count():
        collapse.click()
        expand.click()
        add_check(result, f"{prefix}.expand_all_visible", cards.evaluate_all("es=>es.every(e=>!e.hidden&&e.open)"), {"cards": total})
        collapse.click()
        if recommended.count():
            recommended.check()
        expand.click()
        state = cards.evaluate_all("es=>es.map(e=>({id:e.id,hidden:e.hidden,open:e.open}))")
        add_check(result, f"{prefix}.expand_current", all(c["open"] != c["hidden"] for c in state), state)
        collapse.click()
        add_check(result, f"{prefix}.collapse_all", cards.evaluate_all("es=>es.every(e=>!e.open)"))
        if recommended.count():
            recommended.uncheck()
        clear()
    else:
        add_check(result, f"{prefix}.expand_collapse", status="NA", detail="No expand/collapse controls.")


def calculator_values(calc):
    return {e.get_attribute("data-input"): float(e.input_value()) for e in calc.locator("[data-input]").all()}


def allocation_expected(values):
    due = values["income"] * values["share"] / 100 * values["efficiency"] / 100 * values["months"]
    paid = min(due, values["cash"])
    return {"due": due, "paid": paid, "arrears": due - paid}


def output_matches(calc, expected):
    actual = {e.get_attribute("data-output"): e.inner_text().strip() for e in calc.locator("[data-output]").all()}
    try:
        matches = all(math.isfinite(float(actual[k])) and math.isclose(float(actual[k]), value, rel_tol=0, abs_tol=.005001) for k, value in expected.items())
    except (KeyError, ValueError):
        matches = False
    return matches, {"expected_before_display_rounding": expected, "actual": actual}


def check_calculators(page, result, no_js=False):
    calculators = page.locator("[data-calculator]")
    label = "no_js.calculator" if no_js else "calculator"
    if not calculators.count():
        add_check(result, label, status="NA", detail="No calculator in this report.")
        return
    if not no_js:
        mode(page, "full")
        if continuous(page): open_details(page)
    for index, calc in enumerate(calculators.all(), 1):
        kind = calc.get_attribute("data-calculator")
        prefix = f"{label}.{index}.{kind}"
        if kind != "allocation":
            add_check(result, prefix, status="NOT_RUN", detail="Calculator is present but its formula contract has no verifier.")
            continue
        expected = allocation_expected(calculator_values(calc))
        ok, detail = output_matches(calc, expected)
        add_check(result, prefix + ".static_example" if no_js else prefix + ".initial", ok, detail)
        if no_js:
            continue
        reset = calc.locator("[data-reset-calc]")
        initial = {e.get_attribute("data-input"): e.input_value() for e in calc.locator("[data-input]").all()}

        def restore():
            if reset.count():
                reset.click()
            else:
                for field, value in initial.items():
                    calc.locator(f'[data-input="{field}"]').fill(value)

        for field, value, case in (("income", "0", "zero_income"), ("cash", "0", "zero_cash"),
                                   ("share", "100", "share_boundary"), ("efficiency", "100", "efficiency_boundary"),
                                   ("cash", "1000000000", "payment_capped")):
            restore()
            calc.locator(f'[data-input="{field}"]').fill(value)
            ok, detail = output_matches(calc, allocation_expected(calculator_values(calc)))
            add_check(result, f"{prefix}.{case}", ok, detail)
        for field, value, case in (("share", "101", "share_over_limit"), ("efficiency", "101", "efficiency_over_limit"),
                                   ("income", "-1", "negative_income"), ("months", "1.5", "fractional_months"),
                                   ("cash", "", "blank_cash")):
            restore()
            calc.locator(f'[data-input="{field}"]').fill(value)
            outputs = calc.locator("[data-output]").all_text_contents()
            message = calc.locator("[data-calc-message]").inner_text()
            add_check(result, f"{prefix}.{case}", bool(outputs) and all(x.strip() == "—" for x in outputs) and "输入无效" in message,
                      {"outputs": outputs, "message": message})
        restore()


def check_print(page, result):
    if not page.locator("[data-print]").count():
        add_check(result, "print", status="NA", detail="No print feature in this report.")
        return
    mode(page, "focus")
    if continuous(page): open_details(page)
    cards = page.locator(".case-card")
    if cards.count():
        first = cards.first
        if not first.evaluate("e=>e.open"):
            first.locator("summary").first.click()
        for box in page.locator("[data-browser]").all():
            if box.locator("[data-search]").count():
                box.locator("[data-search]").fill("CK3_PRINT_NO_MATCH_28091")
            sorter = box.locator("[data-sort]")
            if sorter.count() and sorter.locator('option[value="title"]').count():
                sorter.select_option("title")
    before = page.evaluate(SNAPSHOT_JS)
    page.evaluate("window.dispatchEvent(new Event('beforeprint'));window.dispatchEvent(new Event('beforeprint'))")
    visibility = section_visibility(page)
    add_check(result, "print.preparation_sections", bool(visibility["count"]) and not visibility["hidden"], visibility)
    details = page.locator("details")
    add_check(result, "print.preparation_details", details.evaluate_all("es=>es.every(e=>e.open)") if details.count() else None,
              status=None if details.count() else "NA", detail={"details": details.count()})
    add_check(result, "print.preparation_cards", cards.evaluate_all("es=>es.every(e=>!e.hidden)") if cards.count() else None,
              status=None if cards.count() else "NA", detail={"cards": cards.count()})
    page.emulate_media(media="print")
    visibility = section_visibility(page)
    add_check(result, "print.media_sections", bool(visibility["count"]) and not visibility["hidden"], visibility)
    page.emulate_media(media="screen")
    page.evaluate("window.dispatchEvent(new Event('afterprint'));window.dispatchEvent(new Event('afterprint'))")
    after = page.evaluate(SNAPSHOT_JS)
    add_check(result, "print.state_restored", before == after, {"before": before, "after": after})


def check_no_js(browser, path, out, result):
    context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844}, service_workers="block")
    try:
        page = context.new_page()
        page.set_default_timeout(4000)
        monitor(context, page, result, "no_js")
        go(page, path)
        for width, height in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": height})
            if continuous(page):
                for detail in page.locator('[data-local-detail]').all():
                    if not detail.evaluate('e=>e.open'): detail.locator(':scope > summary').click()
                add_check(result,f'no_js.native_disclosure.{width}',page.locator('[data-local-detail]').evaluate_all('es=>es.every(e=>e.open)'))
            visibility = section_visibility(page)
            add_check(result, f"no_js.sections.{width}", visibility["count"] == 16 and not visibility["hidden"], visibility)
            layout_check(page, result, f"no_js.layout.{width}")
        page.set_viewport_size({"width": 390, "height": 844})
        controls = page.locator(".enhancement-only")
        add_check(result, "no_js.controls_hidden", controls.evaluate_all("es=>es.every(e=>getComputedStyle(e).display==='none')") if controls.count() else None,
                  status=None if controls.count() else "NA", detail={"enhancement_containers": controls.count()})
        for name, selector in (("card", ".case-card"), ("source", ".source-block")):
            items = page.locator(selector)
            if not items.count():
                add_check(result, f"no_js.native_{name}", status="NA", detail="No matching native details in this report.")
                continue
            first = items.first
            before = first.evaluate("e=>e.open")
            first.locator("summary").first.click()
            after = first.evaluate("e=>e.open")
            add_check(result, f"no_js.native_{name}", before != after)
        check_calculators(page, result, no_js=True)
        page.evaluate("scrollTo(0,0)")
        screenshot(page, out, result, "390_no_js")
    finally:
        context.close()


def audit_report(browser, path, out, number):
    prefix = f'{number:02d}_' + re.sub(r"[^\w.-]", "_", path.stem)[:70]
    result = {"path": str(path), "uri": path.as_uri(), "artifact_prefix": prefix,
              "checks": [], "screenshots": [], "page_errors": [], "external_requests": []}
    if not path.is_file():
        add_check(result, "input", status="NOT_RUN", detail="Report file does not exist.")
        return finalize(result)
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    result["sha256"] = original_hash
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1, service_workers="block")
    try:
        page = context.new_page()
        page.set_default_timeout(4000)
        monitor(context, page, result, "javascript_enabled")
        go(page, path)
        result["features"] = {"sections": page.locator("[data-section]").count(),
                              "cards": page.locator(".case-card").count(),
                              "card_browsers": page.locator("[data-browser]").count(),
                              "calculators": page.locator("[data-calculator]").count()}
        add_check(result, "file_protocol", page.url.startswith("file:"), {"actual_url": page.url})
        add_check(result, "sections.count", result["features"]["sections"] == 16, result["features"])
        if page.locator("[data-mode]").count():
            add_check(result, "enhancement.initialized", page.locator("body").evaluate("e=>e.classList.contains('enhanced')&&e.classList.contains('focus-mode')"))

        # Independent groups continue after a group error; a timeout never becomes PASS.
        groups = [("layouts", lambda: check_layouts(page, path, out, result)),
                  ("navigation", lambda: check_navigation(page, result))]
        for name, operation in groups:
            try:
                operation()
            except Exception as exc:
                add_check(result, name + ".execution", status="ERROR", detail=str(exc))
                go(page, path)
        mode(page, "full")
        if continuous(page): open_details(page)
        boxes = page.locator("[data-browser]")
        if not boxes.count():
            for group in CARD_GROUPS:
                add_check(result, "browser." + group, status="NA", detail="No card-browser component in this report.")
        for index in range(boxes.count()):
            try:
                check_card_browser(boxes.nth(index), result, index + 1)
            except Exception as exc:
                add_check(result, f"browser.{index+1}.execution", status="ERROR", detail=str(exc))
        for name, operation in (("calculator", lambda: check_calculators(page, result)),
                                ("print", lambda: check_print(page, result))):
            try:
                go(page, path)
                operation()
            except Exception as exc:
                add_check(result, name + ".execution", status="ERROR", detail=str(exc))
    except Exception as exc:
        add_check(result, "browser.execution", status="ERROR", detail=str(exc))
    finally:
        context.close()
    try:
        check_no_js(browser, path, out, result)
    except Exception as exc:
        add_check(result, "no_js.execution", status="ERROR", detail=str(exc))
    add_check(result, "page_errors", not result["page_errors"], result["page_errors"])
    add_check(result, "external_requests", not result["external_requests"], result["external_requests"])
    add_check(result, "input_unchanged", path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == original_hash)
    return finalize(result)


def summarize(result):
    checks = list(result.get("checks", []))
    for report in result["reports"]:
        checks.extend(report["checks"])
    aggregate = finalize({"checks": checks})
    result.update({key: aggregate[key] for key in ("status", "passed", "counts")})
    result["report_counts"] = dict(Counter(report["status"] for report in result["reports"]))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path, help="Actual generated HTML files to audit; no implicit example selection.")
    parser.add_argument("--browser", type=Path, help="Chromium-compatible browser executable (optional).")
    parser.add_argument("--output", type=Path, required=True, help="Directory for results.json and viewport screenshots.")
    args = parser.parse_args(argv)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "load_method": "file://",
              "requested_reports": [str(p.resolve()) for p in args.reports], "checks": [], "reports": [],
              "game_runtime": "NOT_RUN", "semantic_review": "NOT_RUN",
              "notes": ["Uses supplied files only; does not replace card data or repair report CSS.",
                        "External resource attempts are recorded and blocked.",
                        "Print events and CSS media are tested; OS print dialog, pagination, and physical output are NOT_RUN.",
                        "NA means the feature is absent or cannot demonstrate the claimed behavior; NOT_RUN is incomplete coverage."]}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        add_check(result, "browser.available", status="NOT_RUN", detail=f"Playwright is unavailable: {exc}")
    else:
        try:
            with sync_playwright() as pw:
                executable = str(args.browser.resolve()) if args.browser else default_executable()
                options = {"headless": True}
                if executable:
                    options["executable_path"] = executable
                try:
                    browser = pw.chromium.launch(**options)
                except Exception as exc:
                    add_check(result, "browser.available", status="NOT_RUN", detail=str(exc))
                else:
                    result["browser"] = {"version": browser.version, "executable": executable or "Playwright configured Chromium"}
                    try:
                        for number, path in enumerate(args.reports, 1):
                            result["reports"].append(audit_report(browser, path.resolve(), out, number))
                    finally:
                        browser.close()
        except Exception as exc:
            add_check(result, "browser.harness", status="ERROR", detail=str(exc))
    summarize(result)
    destination = out / "results.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "passed": result["passed"], "counts": result["counts"],
                      "report_counts": result["report_counts"], "output": str(destination),
                      "reports": [{"path": r["path"], "status": r["status"], "counts": r["counts"],
                                   "failed": [{"name": c["name"], "status": c["status"]} for c in r["checks"]
                                              if c["status"] in ("FAIL", "ERROR", "NOT_RUN")]} for r in result["reports"]],
                      "execution": result["checks"]}, ensure_ascii=False, indent=2))
    return exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
