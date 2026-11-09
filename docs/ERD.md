# Database schema (ERD)

GitHub draws this diagram automatically from the text below (Mermaid).

```mermaid
erDiagram
    USER ||--o{ DOCUMENT : "owns"
    USER ||--o{ DOCUMENT_ACCESS : "is shared"
    DOCUMENT ||--o{ DOCUMENT_ACCESS : "is shared with"
    DOCUMENT ||--o{ ACTIVITY_LOG : "has history"
    USER |o--o{ ACTIVITY_LOG : "did"
    DOCUMENT ||--o{ DOCUMENT_VERSION : "has versions"
    USER |o--o{ DOCUMENT_VERSION : "saved"

    USER {
        bigint id PK
        string email UK "login"
        string display_name "shown to collaborators"
        string password "hashed"
        bool is_active
        datetime date_joined
    }
    DOCUMENT {
        uuid id PK "random: URLs cannot be guessed"
        bigint owner_id FK
        string title
        binary yjs_state "full Yjs CRDT state"
        datetime created_at
        datetime updated_at
    }
    DOCUMENT_ACCESS {
        bigint id PK
        uuid document_id FK
        bigint user_id FK
        string role "editor | viewer"
        bigint invited_by_id FK "nullable"
        datetime created_at
    }
    ACTIVITY_LOG {
        bigint id PK
        uuid document_id FK
        bigint actor_id FK "nullable: kept if the user is deleted"
        string action "created, renamed, edited, shared..."
        json metadata "details, e.g. old and new title"
        datetime created_at
    }
    DOCUMENT_VERSION {
        bigint id PK
        uuid document_id FK
        bigint created_by_id FK "nullable"
        string label
        string kind "manual | backup"
        binary yjs_state "snapshot"
        datetime created_at
    }
```

## Rules the schema enforces

| Rule | How |
|---|---|
| One role per person per document | `UNIQUE (document_id, user_id)` on `DOCUMENT_ACCESS` |
| The owner is not stored as a member | Ownership lives on `DOCUMENT.owner_id`; `DOCUMENT_ACCESS` holds only `editor` / `viewer` |
| Deleting a document removes its sharing, history and versions | `ON DELETE CASCADE` from `DOCUMENT` |
| Deleting a user keeps the history readable | `actor_id` / `created_by_id` become `NULL` (`SET NULL`); the UI shows "deleted user" |
| Fast lists and history | Indexes on `(owner_id, updated_at)`, `(document_id, created_at)` |

The live content is a Yjs CRDT state (`yjs_state`), not HTML: that is what lets
several people type at the same time without conflicts.
