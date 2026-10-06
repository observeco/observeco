-- consent records: spec 095 s3.2 and s7.7
--
-- WHY THIS IS ITS OWN TABLE AND NOT A BOOLEAN ON THE CONTACT
-- ---------------------------------------------------------
-- Spec 3.2: "A single checkbox covering both is the common PDPA failure. The
-- architecture carries per-purpose consent rows, so withdrawing one does not revoke
-- the other." Spec 7.7: "Consent must be evidenced per purpose. One 'agreed to
-- terms' row cannot prove WHICH purposes were agreed."
--
-- A consent flag on the contact row cannot answer the question a regulator asks:
-- WHAT did this person agree to, WHEN, and on the basis of WHICH words? So this is
-- append-only and per-purpose, and it records the notice VERSION that was shown --
-- because if the wording changes, the old consent was given to different words.
--
-- THE THREE PURPOSES (spec 7.7), and they must never be bundled:
--   1  deliver the requested report      -- required to perform what was asked
--   2  follow-up / nurture               -- optional, separate
--   3  aggregate market research         -- optional, separate
--
-- Purpose 1 has no consent row by design: it is the act the person asked for, not a
-- permission they granted. Recording it as "consent" would blur the distinction the
-- spec draws. It is still recorded here as an ACKNOWLEDGEMENT so the notice version
-- shown at submission is evidenced.

create table if not exists consent_records (
    id              bigserial primary key,
    email           text        not null,
    purpose         smallint    not null check (purpose in (1, 2, 3)),
    granted         boolean     not null,
    notice_version  text        not null,
    notice_hash     text        not null,
    granted_at      timestamptz not null default now(),
    withdrawn_at    timestamptz,
    source          text        not null default 'business_review_form'
);

-- one live record per (email, purpose); re-consent updates rather than duplicates,
-- so "what is currently agreed" is a single indexed lookup
create unique index if not exists consent_records_live_idx
    on consent_records (lower(email), purpose)
    where withdrawn_at is null;

create index if not exists consent_records_email_idx on consent_records (lower(email));

-- ⚠ DELIBERATELY NO DEFAULT-ON. A pre-ticked box is not consent under the PDPA
-- (spec 7.7, rule 1). `granted` must be written from an explicit act, and the column
-- has no default so a caller that forgets to pass it fails rather than silently
-- recording agreement.
