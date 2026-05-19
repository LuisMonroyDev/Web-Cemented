# 00 — Overview

## What this is

A single-page website for a band that lets visitors:
1. Learn who the band is (visual identity + brief context)
2. Listen to the music (embedded player from existing streaming service)
3. Buy merch (currently shirts; vinyl/CDs/posters likely within a year)

The site mirrors the live-show experience: encounter the band → hear the music
→ take something home.

## Who it's for

Three audiences, currently roughly equal in volume:
- **Existing fans** who saw a live show and want to buy/reorder
- **New listeners** who found the band online and want to learn more
- **Cold strangers** arriving from social shares

The page order (logo → music → merch) is intentional: it serves cold visitors
first (hook them with music) and lets warm visitors scroll past to merch.

## The v1 — single sentence

A one-page React site that shows the band's identity and music, with a working
shirt-buying flow powered by a Django/Postgres backend and Stripe Checkout,
shipping to US only.

## Explicit non-goals for v1

These are NOT in scope and should not be built. Each can come later, in its
own feature chat.

- **Customer accounts.** Guest checkout only. Orders attach to an email.
- **Multi-page navigation.** No /about, /shows, /blog. One page.
- **PayPal or alternative payment processors.** Stripe only.
- **International shipping.** US only.
- **Real-time inventory across multiple sales channels.** The website's
  inventory is independent of in-person sales at shows for v1. Manual
  reconciliation through the Django admin is acceptable.
- **Custom audio player.** Embed Spotify/Bandcamp/SoundCloud. Do not build
  a player from scratch.
- **A blog, mailing list signup, fan forum, or social features.** Out of scope.

## What "done" looks like for v1

- Visitor can land on the homepage and see logo, gallery/visual, embedded
  music player, and merch grid
- Visitor can click a shirt, pick a size, add to cart, and check out
- Stripe Checkout collects payment and shipping info
- Successful order: customer receives confirmation email, band receives
  notification email, order appears in Django admin
- Stock decrements correctly when an order is placed
- The band can manage products and inventory through the Django admin

## Exit ramps (built into v1 to support future features)

- Product model supports variants (size, color) and can hold non-shirt
  products without schema changes
- Order model attaches to email, with a nullable `user_id` so accounts can
  be added later without migrating old orders
- The single page is structured in clear sections so a future `/store` route
  can host an expanded catalog without rewriting the storefront
