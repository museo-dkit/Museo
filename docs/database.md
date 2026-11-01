# Database overview

Modu uses MySQL as the main persistence layer for the app’s wardrobe, catalog, and try-on workflows.

The core tables are:

- `users`: stores authenticated users and their basic profile information.
- `body_measurements`: stores each user’s body measurements used to fit the avatar.
- `owned_clothes`: tracks clothes already in a user’s wardrobe, including tags, colour, brand, and image metadata.
- `shops` and `shop_products`: store merchant and product catalog data for real-world items users can browse and save. `shop_products.is_example` marks sample/demo products and defaults to `false`.
- `saved_items`: links users to products they liked.
- `outfits` and `outfit_items`: represent composed outfits, built from either owned clothes or shop products.
- `size_charts`: stores product sizing information for fitting and recommendations.
- `try_on_jobs`: tracks background AI try-on jobs, their status, and result image URLs.


### ERD 
Can also be accessed from this [link](https://dbdiagram.io/d/modu_erd-6ad79e08f8963ca19c64cf23)
![Database schema](mode_schema.png)

The schema is subject to change as our project evolves.