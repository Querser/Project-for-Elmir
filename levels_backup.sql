--
-- PostgreSQL database dump
--

\restrict x1QgOKgUQHijWr4WCVMukOPDxKX21Per7Z8Cy0LhBJDxCU0KUeXdW2HOImf78tk

-- Dumped from database version 16.11 (Debian 16.11-1.pgdg13+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: levels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.levels (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(500),
    sort_order integer NOT NULL
);


ALTER TABLE public.levels OWNER TO postgres;

--
-- Name: levels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.levels_id_seq OWNER TO postgres;

--
-- Name: levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.levels_id_seq OWNED BY public.levels.id;


--
-- Name: levels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.levels ALTER COLUMN id SET DEFAULT nextval('public.levels_id_seq'::regclass);


--
-- Data for Name: levels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.levels (id, name, description, sort_order) FROM stdin;
7	╨Э╨╛╨▓╨╕╤З╨╛╨║	\N	0
8	╨Ы╤О╨▒╨╕╤В╨╡╨╗╤М	\N	0
9	╨Я╤А╨╛╤Д╨╕	\N	0
\.


--
-- Name: levels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.levels_id_seq', 9, true);


--
-- Name: levels levels_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.levels
    ADD CONSTRAINT levels_name_key UNIQUE (name);


--
-- Name: levels levels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.levels
    ADD CONSTRAINT levels_pkey PRIMARY KEY (id);


--
-- Name: ix_levels_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_levels_id ON public.levels USING btree (id);


--
-- PostgreSQL database dump complete
--

\unrestrict x1QgOKgUQHijWr4WCVMukOPDxKX21Per7Z8Cy0LhBJDxCU0KUeXdW2HOImf78tk

