CREATE DATABASE IF NOT EXISTS modu;
USE modu;

CREATE TABLE users (
    id CHAR(36) PRIMARY KEY,
    google_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE body_measurements (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL UNIQUE,
    height_cm DECIMAL(5,2),
    weight_kg DECIMAL(5,2),
    bust_cm DECIMAL(5,2),
    waist_cm DECIMAL(5,2),
    hip_cm DECIMAL(5,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL,

    CONSTRAINT fk_body_measurements_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE owned_clothes (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(80),
    brand VARCHAR(100),
    color VARCHAR(80),
    tags JSON,
    embedding JSON,
    size_label VARCHAR(30),
    image_s3_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_owned_clothes_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE shops (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    website_url TEXT
);

CREATE TABLE shop_products (
    id CHAR(36) PRIMARY KEY,
    shop_id CHAR(36) NOT NULL,
    external_product_id VARCHAR(150),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(80),
    color VARCHAR(80),
    tags JSON,
    embedding JSON,
    image_s3_url TEXT,
    product_url TEXT,
    price DECIMAL(10,2),
    is_example BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_shop_products_shop
        FOREIGN KEY (shop_id) REFERENCES shops(id),

    UNIQUE INDEX uq_shop_external_product
        (shop_id, external_product_id)
);

CREATE TABLE size_charts (
    id CHAR(36) PRIMARY KEY,
    shop_product_id CHAR(36) NOT NULL,
    size_label VARCHAR(30) NOT NULL,
    chest_cm DECIMAL(5,2),
    waist_cm DECIMAL(5,2),
    hip_cm DECIMAL(5,2),
    inseam_cm DECIMAL(5,2),
    length_cm DECIMAL(5,2),

    CONSTRAINT fk_size_charts_product
        FOREIGN KEY (shop_product_id) REFERENCES shop_products(id)
);

CREATE TABLE saved_items (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    shop_product_id CHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_saved_items_user
        FOREIGN KEY (user_id) REFERENCES users(id),

    CONSTRAINT fk_saved_items_product
        FOREIGN KEY (shop_product_id) REFERENCES shop_products(id),

    UNIQUE INDEX uq_saved_user_product
        (user_id, shop_product_id)
);

CREATE TABLE outfits (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    preview_image_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL,

    CONSTRAINT fk_outfits_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE outfit_items (
    id CHAR(36) PRIMARY KEY,
    outfit_id CHAR(36) NOT NULL,
    owned_clothes_id CHAR(36),
    shop_product_id CHAR(36),

    CONSTRAINT fk_outfit_items_outfit
        FOREIGN KEY (outfit_id) REFERENCES outfits(id),

    CONSTRAINT fk_outfit_items_owned_clothes
        FOREIGN KEY (owned_clothes_id) REFERENCES owned_clothes(id),

    CONSTRAINT fk_outfit_items_shop_product
        FOREIGN KEY (shop_product_id) REFERENCES shop_products(id),

    CONSTRAINT chk_outfit_item_source CHECK (
        (owned_clothes_id IS NOT NULL AND shop_product_id IS NULL)
        OR
        (owned_clothes_id IS NULL AND shop_product_id IS NOT NULL)
    ),

    UNIQUE INDEX uq_outfit_owned_clothes
        (outfit_id, owned_clothes_id),

    UNIQUE INDEX uq_outfit_shop_product
        (outfit_id, shop_product_id)
);

CREATE TABLE try_on_jobs (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    outfit_id CHAR(36),
    result_s3_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    provider VARCHAR(80),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_try_on_job_status
        CHECK (status IN ('pending', 'done', 'failed')),

    CONSTRAINT fk_try_on_jobs_user
        FOREIGN KEY (user_id) REFERENCES users(id),

    CONSTRAINT fk_try_on_jobs_outfit
        FOREIGN KEY (outfit_id) REFERENCES outfits(id)
);
