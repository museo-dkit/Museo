# H&M sample catalogue

Scripts to select a varied H&M sample from Kaggle, download its product photos,
and import the products into the local Modu database.

## Setup

- Put Kaggle's [`articles.csv`](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data?select=articles.csv) in `~/Downloads`.
- Configure Kaggle API credentials and accept the dataset rules on Kaggle.
- Install the script dependencies:

```bash
python3 -m venv ~/venvs/modu-hm-catalogue
source ~/venvs/modu-hm-catalogue/bin/activate
python -m pip install -r tools/hm_catalogue/requirements.txt
```

## Select products and download photos

```bash
python tools/hm_catalogue/select_articles.py
```

By default, this selects 2,000 varied articles, saves
`~/Downloads/selected_articles.csv`, and downloads valid JPEGs to
`~/Downloads/hm_catalogue/images/`. The script resumes using cached images.
If Kaggle rate-limits the downloads, wait and rerun it. Review the photos for
visual suitability; the script checks that they are readable JPEGs, not that
the product photo is clean.

## Import into local MySQL

Start Docker Desktop. From the repository root, start MySQL and apply database
migrations:

```bash
docker compose up -d mysql
cd backend
source .venv/bin/activate
alembic upgrade head
cd ..
```

Validate the CSV and photos, then import:

```bash
backend/.venv/bin/python -m tools.hm_catalogue.import_articles --dry-run
backend/.venv/bin/python -m tools.hm_catalogue.import_articles
```

The importer reads `backend/.env` for its database connection. It creates or
updates products in the `H&M Kaggle Examples` shop, with `price=NULL` and
`is_example=true`. The photos stay on your computer; `image_s3_url` stores
future S3 keys under `hm/articles/images/`. Uploading to S3 and displaying the
photos in the app require separate setup.

Keep the CSV, downloaded photos, and Kaggle credentials out of Git.
