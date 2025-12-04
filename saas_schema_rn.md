# 📘 Modelo de Tabelas e Regras de Negócio (RN)

Este documento descreve **apenas** as tabelas e regras de negócio relacionadas a:

- `users`
- `subscriptions`
- `plans`
- `conversion_requests`
- `billing_events`

---

# 🗂️ 1. Tabela: `users`
Guarda os dados dos usuários cadastrados.

### **Campos**
- `id` — uuid (PK)
- `name` — text
- `email` — text (unique)
- `password_hash` — text
- `is_active` — boolean
- `last_login` — timestamp
- `created_at` — timestamp
- `updated_at` — timestamp

### **RNs relacionadas**
#### **RN-U01 — Cadastro**
O usuário deve fornecer e-mail único e senha válida.

#### **RN-U02 — Login**
O sistema valida o hash da senha; se falhar, negar acesso.

#### **RN-U03 — Ativação**
Usuário só pode usar o sistema se `is_active = true`.

#### **RN-U04 — Acesso ao SaaS**
Toda ação relevante deve estar vinculada a um usuário ativo.

---

# 🗂️ 2. Tabela: `plans`
Define os planos de assinatura do SaaS.

### **Campos**
- `id` — uuid (PK)
- `name` — text
- `price` — decimal
- `period` — enum(`monthly`, `yearly`)
- `max_conversions_per_month` — int
- `max_video_length_minutes` — int
- `allow_mp3` — boolean
- `allow_mp4` — boolean
- `allow_hd` — boolean
- `created_at` — timestamp
- `updated_at` — timestamp

### **RNs relacionadas**
#### **RN-P01 — Limites por Plano**
Cada plano define limites de uso (conversões, duração do vídeo etc.).

#### **RN-P02 — Permissão de Formato**
O plano define se o usuário pode converter para MP3 e/ou MP4.

#### **RN-P03 — Qualidade Permitida**
Plano pode restringir qualidade (ex: HD apenas em planos pagos).

#### **RN-P04 — Preço e Ciclo**
Cada plano possui um valor e período (mensal/anual).

---

# 🗂️ 3. Tabela: `subscriptions`
Registra o plano ativo de cada usuário.

### **Campos**
- `id` — uuid (PK)
- `user_id` — uuid (FK → users.id)
- `plan_id` — uuid (FK → plans.id)
- `status` — enum(`active`, `canceled`, `expired`)
- `start_date` — date
- `end_date` — date
- `cancel_at_period_end` — boolean

### **RNs relacionadas**
#### **RN-S01 — Um plano por usuário**
Um usuário só pode ter **uma assinatura ativa por vez**.

#### **RN-S02 — Expiração**
Quando `end_date < hoje`, assinatura vira `expired`.

#### **RN-S03 — Cancelamento**
Se usuário cancelar, a assinatura permanece ativa até `end_date`.

#### **RN-S04 — Plano Free**
Novo usuário inicia com plano `Free` automaticamente.

#### **RN-S05 — Mudança de Plano**
Ao trocar de plano, criar novo registro e encerrar o anterior.

---

# 🗂️ 4. Tabela: `conversion_requests`
Registra cada solicitação de conversão.

### **Campos**
- `id` — uuid (PK)
- `user_id` — uuid (FK → users.id)
- `input_url` — text
- `format_requested` — enum(`mp3`, `mp4`)
- `quality_requested` — text
- `status` — enum(`queued`, `processing`, `completed`, `failed`)
- `file_path` — text (nullable)
- `file_size_mb` — decimal
- `video_length_seconds` — int
- `created_at` — timestamp
- `completed_at` — timestamp (nullable)

### **RNs relacionadas**
#### **RN-C01 — Registro Obrigatório**
Toda conversão deve gerar um registro nesta tabela.

#### **RN-C02 — Status da Conversão**
O status deve evoluir dentro do fluxo:
`queued → processing → completed | failed`.

#### **RN-C03 — Limites de Uso**
Antes de iniciar uma conversão:
- verificar limite mensal do plano
- verificar se o formato é permitido
- verificar se a qualidade é permitida
- verificar tamanho/duração do vídeo

#### **RN-C04 — Propriedade do Arquivo**
O arquivo gerado pertence **apenas ao usuário** que solicitou.

#### **RN-C05 — Expiração do Arquivo**
Arquivos devem ter política de expiração definida (ex: 24h).

---

# 🗂️ 5. Tabela: `billing_events`
Armazena eventos financeiros relacionados a cobranças.

### **Campos**
- `id` — uuid (PK)
- `user_id` — uuid (FK → users.id)
- `plan_id` — uuid
- `amount` — decimal
- `currency` — text
- `payment_provider` — text
- `provider_reference` — text
- `status` — enum(`paid`, `pending`, `failed`)
- `created_at` — timestamp

### **RNs relacionadas**
#### **RN-B01 — Registro Obrigatório de Cobranças**
Toda tentativa de cobrança gera um evento.

#### **RN-B02 — Atualização da Assinatura**
Quando `status = paid`:
- assinatura vira `active`
- `start_date` e `end_date` devem ser ajustados

#### **RN-B03 — Falha de Pagamento**
Quando `status = failed`:
- assinatura deve mudar para `expired` após X tentativas

#### **RN-B04 — Integração com Provedores**
Todos os eventos devem armazenar referência do provedor (Stripe, PayPal etc.).

---

# ✅ Conclusão
Este documento apresenta a estrutura mínima necessária para operar um SaaS de conversão de vídeos com controle de usuários, assinaturas, limites de uso e billing.