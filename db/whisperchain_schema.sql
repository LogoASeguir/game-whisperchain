--
-- PostgreSQL database dump
--

\restrict DnYzumJPuJo6RjoOTAuFbG4UcPD2aK6a4sfVKIo5riCbUJV09PvvqKqogJfhMfm

-- Dumped from database version 18.2
-- Dumped by pg_dump version 18.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- Name: game_history; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.game_history (
    id integer NOT NULL,
    room_code character varying(10),
    username character varying(50),
    rounds_played integer,
    final_signal integer,
    placement integer,
    total_players integer,
    played_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.game_history OWNER TO "RDev";

--
-- Name: game_history_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.game_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.game_history_id_seq OWNER TO "RDev";

--
-- Name: game_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.game_history_id_seq OWNED BY public.game_history.id;


--
-- Name: games; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.games (
    id integer CONSTRAINT game_id_not_null NOT NULL,
    room_code text CONSTRAINT game_room_code_not_null NOT NULL,
    status text DEFAULT 'waiting'::text,
    current_round integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT now(),
    scoreboard jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT game_status_check CHECK ((status = ANY (ARRAY['waiting'::text, 'active'::text, 'finished'::text])))
);


ALTER TABLE public.games OWNER TO "RDev";

--
-- Name: game_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.game_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.game_id_seq OWNER TO "RDev";

--
-- Name: game_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.game_id_seq OWNED BY public.games.id;


--
-- Name: game_players; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.game_players (
    id integer NOT NULL,
    game_id integer,
    user_id integer,
    "position" integer NOT NULL,
    joined_at timestamp without time zone DEFAULT now(),
    status text DEFAULT 'Idle'::text,
    location text DEFAULT 'Login'::text
);


ALTER TABLE public.game_players OWNER TO "RDev";

--
-- Name: game_players_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.game_players_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.game_players_id_seq OWNER TO "RDev";

--
-- Name: game_players_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.game_players_id_seq OWNED BY public.game_players.id;


--
-- Name: games_history; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.games_history (
    id integer NOT NULL,
    room_code text NOT NULL,
    num_players integer,
    rounds jsonb,
    created_at timestamp without time zone DEFAULT now(),
    closed_at timestamp without time zone
);


ALTER TABLE public.games_history OWNER TO "RDev";

--
-- Name: games_history_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.games_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.games_history_id_seq OWNER TO "RDev";

--
-- Name: games_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.games_history_id_seq OWNED BY public.games_history.id;


--
-- Name: message_chain; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.message_chain (
    id integer NOT NULL,
    game_id integer,
    round_number integer NOT NULL,
    "position" integer NOT NULL,
    from_player_id integer,
    to_player_id integer,
    text text NOT NULL,
    mutation_applied double precision DEFAULT 0.0,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.message_chain OWNER TO "RDev";

--
-- Name: message_chain_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.message_chain_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.message_chain_id_seq OWNER TO "RDev";

--
-- Name: message_chain_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.message_chain_id_seq OWNED BY public.message_chain.id;


--
-- Name: room_players; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.room_players (
    id integer NOT NULL,
    room_id integer,
    user_id integer,
    is_ready boolean DEFAULT false,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.room_players OWNER TO "RDev";

--
-- Name: room_players_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.room_players_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.room_players_id_seq OWNER TO "RDev";

--
-- Name: room_players_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.room_players_id_seq OWNED BY public.room_players.id;


--
-- Name: rooms; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.rooms (
    id integer NOT NULL,
    code character varying(10) NOT NULL,
    created_by integer,
    status character varying(20) DEFAULT 'waiting'::character varying,
    max_players integer DEFAULT 10,
    current_round integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_activity timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.rooms OWNER TO "RDev";

--
-- Name: rooms_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.rooms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rooms_id_seq OWNER TO "RDev";

--
-- Name: rooms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.rooms_id_seq OWNED BY public.rooms.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: RDev
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username text NOT NULL,
    signal_strength integer DEFAULT 70,
    created_at timestamp without time zone DEFAULT now(),
    last_seen timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_temporary boolean DEFAULT true,
    CONSTRAINT users_signal_strength_check CHECK (((signal_strength >= 0) AND (signal_strength <= 100)))
);


ALTER TABLE public.users OWNER TO "RDev";

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: RDev
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO "RDev";

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: RDev
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: game_history id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_history ALTER COLUMN id SET DEFAULT nextval('public.game_history_id_seq'::regclass);


--
-- Name: game_players id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_players ALTER COLUMN id SET DEFAULT nextval('public.game_players_id_seq'::regclass);


--
-- Name: games id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.games ALTER COLUMN id SET DEFAULT nextval('public.game_id_seq'::regclass);


--
-- Name: games_history id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.games_history ALTER COLUMN id SET DEFAULT nextval('public.games_history_id_seq'::regclass);


--
-- Name: message_chain id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.message_chain ALTER COLUMN id SET DEFAULT nextval('public.message_chain_id_seq'::regclass);


--
-- Name: room_players id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.room_players ALTER COLUMN id SET DEFAULT nextval('public.room_players_id_seq'::regclass);


--
-- Name: rooms id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.rooms ALTER COLUMN id SET DEFAULT nextval('public.rooms_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: game_history game_history_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_history
    ADD CONSTRAINT game_history_pkey PRIMARY KEY (id);


--
-- Name: games game_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.games
    ADD CONSTRAINT game_pkey PRIMARY KEY (id);


--
-- Name: game_players game_players_game_id_position_key; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_players
    ADD CONSTRAINT game_players_game_id_position_key UNIQUE (game_id, "position");


--
-- Name: game_players game_players_game_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_players
    ADD CONSTRAINT game_players_game_id_user_id_key UNIQUE (game_id, user_id);


--
-- Name: game_players game_players_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_players
    ADD CONSTRAINT game_players_pkey PRIMARY KEY (id);


--
-- Name: games game_room_code_key; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.games
    ADD CONSTRAINT game_room_code_key UNIQUE (room_code);


--
-- Name: games_history games_history_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.games_history
    ADD CONSTRAINT games_history_pkey PRIMARY KEY (id);


--
-- Name: message_chain message_chain_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.message_chain
    ADD CONSTRAINT message_chain_pkey PRIMARY KEY (id);


--
-- Name: room_players room_players_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.room_players
    ADD CONSTRAINT room_players_pkey PRIMARY KEY (id);


--
-- Name: room_players room_players_room_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.room_players
    ADD CONSTRAINT room_players_room_id_user_id_key UNIQUE (room_id, user_id);


--
-- Name: rooms rooms_code_key; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_code_key UNIQUE (code);


--
-- Name: rooms rooms_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_game_players_game; Type: INDEX; Schema: public; Owner: RDev
--

CREATE INDEX idx_game_players_game ON public.game_players USING btree (game_id);


--
-- Name: idx_message_chain_game; Type: INDEX; Schema: public; Owner: RDev
--

CREATE INDEX idx_message_chain_game ON public.message_chain USING btree (game_id, round_number);


--
-- Name: game_players game_players_game_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_players
    ADD CONSTRAINT game_players_game_id_fkey FOREIGN KEY (game_id) REFERENCES public.games(id) ON DELETE CASCADE;


--
-- Name: game_players game_players_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.game_players
    ADD CONSTRAINT game_players_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: message_chain message_chain_from_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.message_chain
    ADD CONSTRAINT message_chain_from_player_id_fkey FOREIGN KEY (from_player_id) REFERENCES public.game_players(id);


--
-- Name: message_chain message_chain_game_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.message_chain
    ADD CONSTRAINT message_chain_game_id_fkey FOREIGN KEY (game_id) REFERENCES public.games(id) ON DELETE CASCADE;


--
-- Name: message_chain message_chain_to_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.message_chain
    ADD CONSTRAINT message_chain_to_player_id_fkey FOREIGN KEY (to_player_id) REFERENCES public.game_players(id);


--
-- Name: room_players room_players_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.room_players
    ADD CONSTRAINT room_players_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE CASCADE;


--
-- Name: room_players room_players_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.room_players
    ADD CONSTRAINT room_players_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: rooms rooms_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: RDev
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO "RDev";


--
-- PostgreSQL database dump complete
--

