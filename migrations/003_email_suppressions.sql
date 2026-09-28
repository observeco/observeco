-- email suppression: spec 095 s6.6 and s3.7
--
-- An unsubscribe must survive a re-import. Updating a contact row is not enough:
-- the next import recreates the row without the flag. Suppression is therefore its
-- own append-only table, and every send path must check it.

create table if not exists email_suppressions (
    email         text primary key,
    reason        text not null default 'unsubscribe',
    suppressed_at timestamptz not null default now()
);

-- fast lookup on the send path
create index if not exists email_suppressions_email_idx on email_suppressions (lower(email));
