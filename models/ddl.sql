-- app_user
create table public.app_user (
  id bigserial not null,
  email character varying(120) not null,
  role character varying(20) not null,
  password_hash text not null,
  created_at timestamp without time zone null,
  constraint app_user_pkey primary key (id),
  constraint app_user_email_key unique (email)
) TABLESPACE pg_default;


-- dislike
create table public.dislike (
  id bigserial not null,
  user_id bigint not null,
  job_id bigint not null,
  disliked_at timestamp without time zone null,
  constraint dislike_pkey primary key (id),
  constraint dislike_job_id_fkey foreign KEY (job_id) references job_listing (id),
  constraint dislike_user_id_fkey foreign KEY (user_id) references app_user (id)
) TABLESPACE pg_default;


-- employer
create table public.employer (
  id bigserial not null,
  name character varying(120) not null,
  contact_email character varying(120) null,
  is_agency boolean null,
  created_at timestamp without time zone null,
  constraint employer_pkey primary key (id)
) TABLESPACE pg_default;


-- job_listing 
create table public.job_listing (
  id bigserial not null,
  employer_id bigint not null,
  title character varying(140) not null,
  description text null,
  location character varying(120) null,
  client character varying(140) null,
  is_active boolean not null default true,
  constraint job_listing_pkey primary key (id),
  constraint job_listing_employer_id_fkey foreign KEY (employer_id) references employer (id)
) TABLESPACE pg_default;


-- match
create table public.match (
  id bigserial not null,
  user_id bigint not null,
  job_id bigint not null,
  matched_at timestamp without time zone null,
  notification_sent boolean null,
  notification_sent_at timestamp without time zone null,
  notification_message text null,
  constraint match_pkey primary key (id),
  constraint match_job_id_fkey foreign KEY (job_id) references job_listing (id),
  constraint match_user_id_fkey foreign KEY (user_id) references app_user (id)
) TABLESPACE pg_default;


-- recruiter_user
create table public.recruiter_user (
  id bigserial not null,
  employer_id bigint null,
  user_id bigint not null,
  is_admin boolean null,
  constraint recruiter_user_pkey primary key (id),
  constraint recruiter_user_employer_id_fkey foreign KEY (employer_id) references employer (id),
  constraint recruiter_user_user_id_fkey foreign KEY (user_id) references app_user (id)
) TABLESPACE pg_default;


-- student
create table public.student (
  id bigserial not null,
  user_id bigint not null,
  first_name character varying(60) null,
  last_name character varying(60) null,
  constraint student_pkey primary key (id),
  constraint student_user_id_fkey foreign KEY (user_id) references app_user (id)
) TABLESPACE pg_default;
