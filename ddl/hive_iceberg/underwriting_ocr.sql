-- =============================================================================
-- Scanned ACORD 125, 126, and 140 — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Prerequisite  : underwriting_iceberg.sql already applied
--
-- One Mistral OCR response is one ocr_document. forms_detected on the sample
-- scan are ACORD 125 (2016/03), ACORD 140 (2016/03), and ACORD 126 (2016/03).
-- Annotation values live on ocr_field. Confidence lives on ocr_page and
-- ocr_word. The payload does not tie a word to a field.
--
-- ACORD 126 paths (acord-125-126-140-confidence.json):
--   acord_126_commercial_general_liability.coverages_and_limits.limits.each_occurrence
--   acord_126_commercial_general_liability.schedule_of_hazards.1.premises_ops_rate
--   acord_126_commercial_general_liability.schedule_of_hazards.1.class_code
--   acord_126_commercial_general_liability.general_liability_underwriting_questions.6.answer
-- Words under 0.8 on that scan: page 8 Rostova 0.691, page 8 Elena 0.738,
-- page 6 55.28 0.768, page 8 Vance 0.795.
-- =============================================================================

USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.ocr_document (
  document_id               STRING    COMMENT 'PK. One Mistral OCR response.',
  submission_id             BIGINT    COMMENT 'FK -> submissions.submission_id.',
  ocr_model                 STRING    COMMENT 'OCR model name, e.g. mistral-ocr-2505.',
  pages_processed           INT       COMMENT 'usage_info.pages_processed.',
  doc_size_bytes            BIGINT    COMMENT 'usage_info.doc_size_bytes.',
  application_date          STRING    COMMENT 'submission_metadata.application_date, ISO-8601.',
  status_of_transaction     STRING    COMMENT 'submission_metadata.status_of_transaction.'
)
COMMENT 'One scanned application. May contain ACORD 125, ACORD 126, and ACORD 140.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'OcrDocument',
  'llm.primary_key' = 'document_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one OCR scan'
);


CREATE TABLE IF NOT EXISTS underwriting.ocr_form (
  form_id                   STRING    COMMENT 'PK. One detected form on a scan.',
  document_id               STRING    COMMENT 'FK -> ocr_document.document_id.',
  submission_id             BIGINT    COMMENT 'FK -> submissions.submission_id.',
  form_label                STRING    COMMENT 'forms_detected entry, e.g. ACORD 126 (2016/03).'
)
COMMENT 'Forms detected on one scan. ACORD 125, 126, and 140 are separate rows.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'OcrForm',
  'llm.primary_key' = 'form_id',
  'llm.foreign_keys' = 'document_id->ocr_document.document_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one detected form'
);


CREATE TABLE IF NOT EXISTS underwriting.ocr_field (
  field_id                  STRING    COMMENT 'PK. One annotation value.',
  document_id               STRING    COMMENT 'FK -> ocr_document.document_id.',
  submission_id             BIGINT    COMMENT 'FK -> submissions.submission_id.',
  field_path                STRING    COMMENT 'Dotted path. Repeating groups use a numeric index, e.g. acord_126_commercial_general_liability.schedule_of_hazards.1.class_code.',
  field_value               STRING    COMMENT 'Annotation value. No confidence; scores are on ocr_word.'
)
COMMENT 'Flattened document_annotation for ACORD 125, ACORD 126, and ACORD 140.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'OcrField',
  'llm.primary_key' = 'field_id',
  'llm.foreign_keys' = 'document_id->ocr_document.document_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one annotated field'
);


CREATE TABLE IF NOT EXISTS underwriting.ocr_page (
  page_id                   STRING    COMMENT 'PK. One page that carried confidence scores.',
  document_id               STRING    COMMENT 'FK -> ocr_document.document_id.',
  submission_id             BIGINT    COMMENT 'FK -> submissions.submission_id.',
  page_index                INT       COMMENT 'pages[].index from the OCR response.',
  average_page_confidence   DOUBLE    COMMENT 'average_page_confidence_score.',
  minimum_page_confidence   DOUBLE    COMMENT 'minimum_page_confidence_score.'
)
COMMENT 'Page-level OCR confidence. Markdown and dimensions are not stored.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'OcrPage',
  'llm.primary_key' = 'page_id',
  'llm.foreign_keys' = 'document_id->ocr_document.document_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one scored page'
);


CREATE TABLE IF NOT EXISTS underwriting.ocr_word (
  word_id                   STRING    COMMENT 'PK. One scored token.',
  document_id               STRING    COMMENT 'FK -> ocr_document.document_id.',
  submission_id             BIGINT    COMMENT 'FK -> submissions.submission_id.',
  page_index                INT       COMMENT 'Page index of the token.',
  word_text                 STRING    COMMENT 'word_confidence_scores[].text.',
  confidence                DOUBLE    COMMENT 'word_confidence_scores[].confidence.'
)
COMMENT 'Word confidence from the OCR response. The review probe reads this table.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'OcrWord',
  'llm.primary_key' = 'word_id',
  'llm.foreign_keys' = 'document_id->ocr_document.document_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one scored word'
);
