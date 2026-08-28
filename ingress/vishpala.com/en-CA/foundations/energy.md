Every page view has an energy cost: power to generate the page, power to move it across the network, and power to render it on a device. A smaller, simpler page lowers all three.

## Less to build

A static site is generated once at build time, not assembled from scratch on every request. There is no server application running around the clock, waking a database for each visitor. Hosting a folder of files draws far less than running a live application stack.

## Less to send

Small pages with subset fonts and minimal script move fewer bytes across the network. Fewer bytes mean less work for every router and radio between the server and the reader — a cost that is easy to ignore because it is spread out, but real.

## Less to run on the device

No heavy trackers run in the background and no analytics pipeline warms up on every visit. The visitor's device is not kept busy doing work that has nothing to do with reading the page, which also means less battery drained on a phone.

## An honest note

We tag this *Inferred* rather than *Verified* on our scorecard, because the gains follow from the architecture — static output, no third-party dependencies — rather than from a measured carbon figure. It is a defensible claim about how the site is built, stated as exactly that. This is part of the *Sustainability* pillar of the Universal Cake Evaluation Metrics.

This is one of our [foundations](/en-ca/foundations/).
