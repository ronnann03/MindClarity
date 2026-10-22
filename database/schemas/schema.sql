-- =====================================================================
-- YU - Esquema de base de datos para Supabase (PostgreSQL + pgvector)
-- =====================================================================
-- Ejecuta este script en el SQL Editor de Supabase.

-- Extensiones necesarias
create extension if not exists "vector";
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------
-- Conversaciones
-- ---------------------------------------------------------------------
create table if not exists conversations (
    id          uuid primary key default gen_random_uuid(),
    title       text,
    summary     text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Mensajes
-- ---------------------------------------------------------------------
create table if not exists messages (
    id              uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    role            text not null check (role in ('user', 'assistant', 'system')),
    content         text not null,
    intent_type     text,
    metadata        jsonb default '{}'::jsonb,
    created_at      timestamptz not null default now()
);
create index if not exists idx_messages_conversation on messages(conversation_id);

-- ---------------------------------------------------------------------
-- Memorias semánticas (con embeddings de 1536 dimensiones)
-- ---------------------------------------------------------------------
create table if not exists memories (
    id          uuid primary key default gen_random_uuid(),
    content     text not null,
    kind        text default 'fact',     -- fact | preference | event | summary
    importance  real default 0.5,
    embedding   vector(1536),
    metadata    jsonb default '{}'::jsonb,
    created_at  timestamptz not null default now()
);
-- Índice ANN para búsqueda por similitud coseno.
create index if not exists idx_memories_embedding
    on memories using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ---------------------------------------------------------------------
-- Tareas y recordatorios
-- ---------------------------------------------------------------------
create table if not exists tasks (
    id          uuid primary key default gen_random_uuid(),
    title       text not null,
    description text,
    status      text default 'pending',  -- pending | done | cancelled
    due_at      timestamptz,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Trigger para actualizar updated_at automáticamente en cada UPDATE.
create or replace function update_updated_at_column()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists tasks_updated_at on tasks;
create trigger tasks_updated_at
    before update on tasks
    for each row execute function update_updated_at_column();

-- ---------------------------------------------------------------------
-- Preferencias del usuario (clave/valor)
-- ---------------------------------------------------------------------
create table if not exists preferences (
    id          uuid primary key default gen_random_uuid(),
    key         text unique not null,
    value       jsonb,
    updated_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Logs del sistema
-- ---------------------------------------------------------------------
create table if not exists system_logs (
    id          uuid primary key default gen_random_uuid(),
    level       text not null,
    message     text not null,
    context     jsonb default '{}'::jsonb,
    created_at  timestamptz not null default now()
);

-- =====================================================================
-- Función RPC para búsqueda vectorial por similitud coseno
-- =====================================================================
create or replace function match_memories(
    query_embedding vector(1536),
    match_threshold float default 0.75,
    match_count int default 5
)
returns table (
    id uuid,
    content text,
    kind text,
    importance real,
    metadata jsonb,
    similarity float
)
language sql stable
as $$
    select
        m.id,
        m.content,
        m.kind,
        m.importance,
        m.metadata,
        1 - (m.embedding <=> query_embedding) as similarity
    from memories m
    where m.embedding is not null
      and 1 - (m.embedding <=> query_embedding) > match_threshold
    order by m.embedding <=> query_embedding
    limit match_count;
$$;

-- =====================================================================
-- Row Level Security (RLS)
-- =====================================================================
alter table conversations enable row level security;
alter table messages      enable row level security;
alter table memories       enable row level security;
alter table tasks          enable row level security;
alter table preferences    enable row level security;
alter table system_logs    enable row level security;

-- Política permisiva para el usuario autenticado / service role.
-- Ajusta según tus necesidades de multiusuario.
do $$
declare
    t text;
begin
    foreach t in array array[
        'conversations','messages','memories','tasks','preferences','system_logs'
    ]
    loop
        execute format(
            'create policy "allow_all_%1$s" on %1$I for all using (true) with check (true);',
            t
        );
    end loop;
exception when duplicate_object then
    null;  -- Las políticas ya existen.
end $$;
