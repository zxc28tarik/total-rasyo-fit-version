-- v2 ratio layer storage.
--
-- v1's analytics.ratios_quarterly and analytics.rsc_summary_quarterly are NOT
-- touched: the existing production line and its regression suite keep running
-- unchanged.  v2 lands beside them, keyed additionally by ratio_set_version, so
-- the same company can be scored under both sets and the difference inspected.
-- That comparison is exactly what the V20 change-impact machinery was built for.

CREATE SCHEMA IF NOT EXISTS analytics;

-- One row per (company, period, disclosure version, ratio set, ratio).
--
-- status replaces v1's single is_na boolean, which conflated three unrelated
-- situations and cost a debt-free company its entire quality score:
--   OK              computed
--   MISSING         a required field is null - lowers coverage
--   BEST / WORST    undefined but economically unambiguous - counts as measured
--   NOT_APPLICABLE  meaningless here - leaves the denominator entirely
CREATE TABLE IF NOT EXISTS analytics.ratios_quarterly_v2 (
  ticker            TEXT NOT NULL,
  period_end        DATE NOT NULL,
  version_tag       TEXT NOT NULL,
  ratio_set_version TEXT NOT NULL,
  ratio_name        TEXT NOT NULL,
  sector_group      TEXT NOT NULL,
  ratio_value       NUMERIC,
  status            TEXT NOT NULL,
  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period_end, version_tag, ratio_set_version, ratio_name),
  CONSTRAINT ratios_v2_status_domain
    CHECK (status IN ('OK', 'MISSING', 'BEST', 'WORST', 'NOT_APPLICABLE')),
  -- An OK row without a value, or a non-OK row carrying one, would let a
  -- fabricated number through under a status that says nothing was measured.
  CONSTRAINT ratios_v2_ok_has_value
    CHECK (status <> 'OK' OR ratio_value IS NOT NULL),
  CONSTRAINT ratios_v2_non_ok_is_null
    CHECK (status = 'OK' OR ratio_value IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_ratios_v2_pe
  ON analytics.ratios_quarterly_v2 (period_end, ratio_set_version);
CREATE INDEX IF NOT EXISTS idx_ratios_v2_ratio
  ON analytics.ratios_quarterly_v2 (ratio_name, period_end);

-- Three composites, not one.  v1 collapsed everything but VAL into a single
-- rsc_core_norm, so growth - a forward-looking signal - was averaged into a
-- backward-looking quality score.
CREATE TABLE IF NOT EXISTS analytics.rsc_summary_v2 (
  ticker            TEXT NOT NULL,
  period_end        DATE NOT NULL,
  version_tag       TEXT NOT NULL,
  ratio_set_version TEXT NOT NULL,
  sector_group      TEXT NOT NULL,

  quality_score     NUMERIC,
  quality_coverage  NUMERIC NOT NULL,
  quality_status    TEXT NOT NULL,
  quality_measured  INT NOT NULL,
  quality_applicable INT NOT NULL,

  growth_score      NUMERIC,
  growth_coverage   NUMERIC NOT NULL,
  growth_status     TEXT NOT NULL,
  growth_measured   INT NOT NULL,
  growth_applicable INT NOT NULL,

  value_score       NUMERIC,
  value_coverage    NUMERIC NOT NULL,
  value_status      TEXT NOT NULL,
  value_measured    INT NOT NULL,
  value_applicable  INT NOT NULL,

  -- Weight share of ratios scoring in the top decile, NOT an absolute count.
  -- v1's good_count_ge8 against a fixed threshold of 5 capped a bank's ek1 at
  -- 10/18 = 0.56 and made the veto 2.6x easier to trip for a bank.
  good_ratio        NUMERIC NOT NULL,

  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period_end, version_tag, ratio_set_version),

  CONSTRAINT rsc_v2_quality_status_domain
    CHECK (quality_status IN ('OK', 'YETERSIZ_KAPSAM')),
  CONSTRAINT rsc_v2_growth_status_domain
    CHECK (growth_status IN ('OK', 'YETERSIZ_KAPSAM')),
  CONSTRAINT rsc_v2_value_status_domain
    CHECK (value_status IN ('OK', 'YETERSIZ_KAPSAM')),

  -- An OK composite must carry a score; an insufficient one must NOT. This is
  -- the database-level half of the "no silent 0.0, no NaN" contract.
  CONSTRAINT rsc_v2_quality_ok_has_score
    CHECK (quality_status <> 'OK' OR quality_score IS NOT NULL),
  CONSTRAINT rsc_v2_growth_ok_has_score
    CHECK (growth_status <> 'OK' OR growth_score IS NOT NULL),
  CONSTRAINT rsc_v2_value_ok_has_score
    CHECK (value_status <> 'OK' OR value_score IS NOT NULL),
  CONSTRAINT rsc_v2_quality_bad_has_no_score
    CHECK (quality_status = 'OK' OR quality_score IS NULL),
  CONSTRAINT rsc_v2_growth_bad_has_no_score
    CHECK (growth_status = 'OK' OR growth_score IS NULL),
  CONSTRAINT rsc_v2_value_bad_has_no_score
    CHECK (value_status = 'OK' OR value_score IS NULL),

  CONSTRAINT rsc_v2_scores_in_unit_range
    CHECK (
      (quality_score IS NULL OR quality_score BETWEEN 0 AND 1) AND
      (growth_score  IS NULL OR growth_score  BETWEEN 0 AND 1) AND
      (value_score   IS NULL OR value_score   BETWEEN 0 AND 1)
    ),
  CONSTRAINT rsc_v2_coverage_in_unit_range
    CHECK (
      quality_coverage BETWEEN 0 AND 1 AND
      growth_coverage  BETWEEN 0 AND 1 AND
      value_coverage   BETWEEN 0 AND 1 AND
      good_ratio       BETWEEN 0 AND 1
    ),
  CONSTRAINT rsc_v2_measured_within_applicable
    CHECK (
      quality_measured BETWEEN 0 AND quality_applicable AND
      growth_measured  BETWEEN 0 AND growth_applicable AND
      value_measured   BETWEEN 0 AND value_applicable
    )
);

CREATE INDEX IF NOT EXISTS idx_rsc_v2_pe
  ON analytics.rsc_summary_v2 (period_end, ratio_set_version);

-- Immutability, matching the pattern already used by the backtest registries
-- (sql/042) and the impact runtime roles (sql/033): a recomputation replaces a
-- row through an explicit DELETE-then-INSERT under a privileged role, never by
-- an in-place UPDATE that would leave no trace of what changed.
CREATE OR REPLACE FUNCTION analytics.ratio_set_v2_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION '% degistirilemez: % denendi', TG_TABLE_NAME, TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS trg_ratios_quarterly_v2_immutable
  ON analytics.ratios_quarterly_v2;
CREATE TRIGGER trg_ratios_quarterly_v2_immutable
    BEFORE UPDATE ON analytics.ratios_quarterly_v2
    FOR EACH ROW EXECUTE FUNCTION analytics.ratio_set_v2_immutable();

DROP TRIGGER IF EXISTS trg_rsc_summary_v2_immutable
  ON analytics.rsc_summary_v2;
CREATE TRIGGER trg_rsc_summary_v2_immutable
    BEFORE UPDATE ON analytics.rsc_summary_v2
    FOR EACH ROW EXECUTE FUNCTION analytics.ratio_set_v2_immutable();
