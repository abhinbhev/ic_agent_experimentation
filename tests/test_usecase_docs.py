from ic_agent.config.usecase_docs import load_schema_doc, load_usecase_docs


def test_load_usecase_docs_uses_domain_knowledge_doc_for_brand_guidance():
    docs = load_usecase_docs("gai_copilot_marketing_brand_guidance_ghq")

    assert "brand_guidance" in docs
    assert "Brand Guidance Knowledge Document" in docs["brand_guidance"]
    assert "category" not in docs


def test_load_usecase_docs_returns_empty_for_unknown_domain():
    docs = load_usecase_docs("does_not_exist")

    assert docs == {}


def test_load_schema_doc_groups_columns_by_table():
    schema = load_schema_doc("gai_copilot_marketing_brand_guidance_ghq")

    assert schema is not None
    assert "### BRAND_DIM" in schema
    assert "`brand_id`: Unique identifier for brand" in schema
    assert "### BG_DIRECT_KPI_FACT" in schema
    assert "`meaningful`: Meaningful KPI value" in schema
    # a table's columns are listed directly under its own heading
    brand_dim_idx = schema.index("### BRAND_DIM")
    brand_id_idx = schema.index("`brand_id`: Unique identifier for brand")
    next_table_idx = schema.index("### COHORT_DIM")
    assert brand_dim_idx < brand_id_idx < next_table_idx


def test_load_schema_doc_returns_none_for_unknown_domain():
    assert load_schema_doc("does_not_exist") is None
