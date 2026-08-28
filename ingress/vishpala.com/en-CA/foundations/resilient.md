A site is only as reliable as everything it quietly depends on. Every external service a page pulls from at load time is another thing that can fail, slow down, or disappear — and take part of your site with it. This one keeps its dependencies to itself.

## Everything served from your own domain

Fonts, scripts, styles, and images are hosted on the site's own domain, not borrowed from a shared CDN or a third-party widget. When the page loads, it asks only its own server for what it needs. There is no external font host to time out, no analytics script to hang, no embedded widget to break the layout when its provider has a bad day.

## Static hosting is hard to knock over

Because the site is a set of static files, there is no application server or database that can crash under load or fall over during a traffic spike. Serving files is one of the most robust things the web does, and it degrades gracefully rather than failing all at once.

## Fewer moving parts, fewer surprises

Each dependency removed is a class of outage that can no longer happen to you. The result is a site whose uptime depends on your own hosting and very little else — something you can reason about and control.

## Where it maps

This is the *Resilience* facet of the *Inclusive* pillar, and it supports *Sustainability*, in the Universal Cake Evaluation Metrics. We tag it *Inferred*: it follows from the architecture of self-hosting and static delivery.

This is one of our [foundations](/en-ca/foundations/).
