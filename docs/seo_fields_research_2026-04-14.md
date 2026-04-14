# SEO Fields Research — 2026-04-14

## Goal

Determine which SEO-related fields should be stored locally for:
- products
- categories
- manual editing in the desktop app
- future import/export to WordPress / WooCommerce
- later AI-assisted filling

## Confirmed project decision

- Active SEO plugin on fisholha.ru: `Yoast SEO`
- SEO implementation is deferred to a later phase
- this document remains the reference for that future phase

## Source summary

### WooCommerce / WordPress core

From official WooCommerce REST API docs:
- WooCommerce product categories expose core fields like:
  - `name`
  - `slug`
  - `parent`
  - `description`
  - `display`
  - `image`
  - `menu_order`
- WooCommerce products expose core editorial fields and `meta_data`.
- This means plugin-specific SEO values for products are typically carried through `meta_data`.

From official WordPress REST API docs:
- posts support `meta`
- categories support `meta`
- custom meta must be registered and exposed in REST to be safely read/write accessible

Inference:
- core WordPress/WooCommerce do not define a universal built-in "SEO fields pack"
- SEO fields depend on the active SEO plugin or a custom metadata model

### Yoast SEO official docs

Yoast official docs describe these important SEO outputs:
- SEO title
- meta description
- canonical URL
- robots meta
- OpenGraph title
- OpenGraph description
- OpenGraph image
- OpenGraph URL
- OpenGraph type
- X/Twitter title
- X/Twitter description
- X/Twitter image

Inference:
- if fisholha.ru uses Yoast SEO, these are the highest-value editable SEO fields to support first

## Recommended local field set

This is the recommended desktop-app field set regardless of the final plugin mapping.

### Common SEO fields for both product and category
- `seo_title`
- `seo_description`
- `seo_canonical_url`
- `seo_robots_index`
- `seo_robots_follow`
- `seo_focus_keyphrase`
- `seo_keywords_notes`

### Social / sharing fields
- `og_title`
- `og_description`
- `og_image_url`
- `twitter_title`
- `twitter_description`
- `twitter_image_url`

### Workflow / AI-preparation fields
- `seo_last_generated_at`
- `seo_last_generated_by`
- `seo_generation_status`
- `seo_notes`

These are local workflow fields, not direct WP/WC fields.

## Import/export model recommendation

### Products
- import/export source:
  - WooCommerce core fields from `wc/v3/products`
  - plugin-specific SEO values via product meta mapping
- if plugin mapping is not available yet:
  - keep fields local-only first
  - add export later after plugin confirmation

### Categories
- import/export source:
  - WooCommerce category core fields from `wc/v3/products/categories`
  - category SEO metadata via WordPress term meta model
- because category SEO usually lives in term meta, exact keys depend on the plugin

## Recommended implementation order

### Safe foundation now
- add local SEO fields to category/product entities
- expose them in desktop edit forms
- allow manual editing only
- do not promise export until plugin mapping is confirmed

### After plugin confirmation
- map local fields to real WordPress/WooCommerce meta keys
- add import from live site
- add export back to live site

### Later AI stage
- keep provider-agnostic generation pipeline
- DeepSeek should be just one provider implementation, not hardcoded architecture

## Important constraint

Without confirming the active SEO plugin, only the local field model can be implemented safely.
Direct import/export key mapping is not reliable yet.

## Sources

Official sources used:
- WooCommerce REST API docs: https://woocommerce.github.io/woocommerce-rest-api-docs/
- WordPress REST API posts reference: https://developer.wordpress.org/rest-api/reference/posts/
- WordPress REST API categories reference: https://developer.wordpress.org/rest-api/reference/categories/
- WordPress `register_post_meta`: https://developer.wordpress.org/reference/functions/register_post_meta/
- WordPress `register_term_meta`: https://developer.wordpress.org/reference/functions/register_term_meta/
- Yoast APIs overview: https://developer.yoast.com/customization/apis/
- Yoast Metadata API: https://developer.yoast.com/customization/apis/metadata-api/
- Yoast REST API: https://developer.yoast.com/customization/apis/rest-api/
- Yoast Surfaces API: https://developer.yoast.com/customization/apis/surfaces-api/
