Accessibility is a property of the build, not a feature we add for some visitors. The same page serves everyone: someone using a screen reader, someone who cannot use a mouse, someone on a small screen in bright sun, and someone who simply wants larger text.

## What ships on every page

Every page is delivered in a shared shell with real landmarks — a `<main>`, a `<nav>`, a `<footer>` — and a skip link that jumps straight to the content. Headings are real headings, in order, never bold text standing in for structure, so the outline a screen reader announces matches the page you see. The document's language and reading direction are set from its locale, so words are pronounced correctly and right-to-left layouts render correctly.

## The Infusion bar

A visitor can adjust the page to their needs without a plugin or an account. The Infusion accessibility bar offers larger text, higher contrast, more spacing, and a reading tool, and it loads only when asked for, so it costs nothing until it is used.

## Motion and input

Animation respects the `prefers-reduced-motion` setting, so the site does not move in ways that cause discomfort. Every interactive element is reachable and operable from the keyboard alone.

## How we hold ourselves to it

The target is WCAG 2.1 AA, and we treat a page that renders inaccessible output as a defect to fix, not an acceptable state. This is the *Inclusive* pillar of the Universal Cake Evaluation Metrics, and it is the one we tag *Verified* — because it is testable, and we test it.

This is one of our [foundations](/en-ca/foundations/).
