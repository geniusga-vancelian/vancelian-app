# Ganopa Evolution Roadmap: From Simple Bot to AI Agent

## Current State

**Ganopa today:**
- Telegram bot with OpenAI integration
- Stateless: one message in, one response out
- No backend connection
- No domain knowledge
- No tools or capabilities
- No memory or context

**Vancelian context:**
- Wealth-tech platform (deposits MVP, vaults planned, RWA planned)
- Principles: simple, regulated, capital-protected first
- Environments: dev, staging, prod

---

## Phase 1: Backend Connection & Authentication

### Goal
Connect Ganopa to Vancelian backend and establish secure user identity.

### Architecture Changes

**1.1 User Identity Layer**
```
Telegram User → Telegram ID → Vancelian User ID
```
- Map Telegram user ID to Vancelian user account
- Support multiple Telegram accounts per Vancelian user
- Handle unlinked accounts (onboarding flow)

**1.2 Authentication Service**
- Ganopa bot calls Vancelian Auth API
- Exchange Telegram user ID for session token
- Token validation on every backend request
- Token refresh mechanism

**1.3 Backend API Client**
- HTTP client library for Vancelian APIs
- Centralized error handling
- Retry logic for transient failures
- Request/response logging

**1.4 Configuration**
- Backend API base URL (per environment)
- API keys or service-to-service auth
- Timeout and retry settings

### Deliverables
- User linking flow (Telegram → Vancelian account)
- Authenticated API client
- Health check endpoint that verifies backend connectivity

### Risks & Mitigations
- **Risk**: Backend downtime breaks bot
- **Mitigation**: Graceful degradation, cache last known state, user notification

---

## Phase 2: Domain Knowledge Base

### Goal
Give Ganopa access to Vancelian product information and user context.

### Architecture Changes

**2.1 Product Knowledge**
- Product catalog API integration
- Real-time product status (available, paused, maintenance)
- Product features, limits, fees
- Regulatory information per product

**2.2 User Context Service**
- User profile API (KYC status, risk profile, preferences)
- Account balance and positions
- Transaction history (filtered, privacy-aware)
- User preferences and settings

**2.3 Knowledge Caching**
- Cache product catalog (TTL: 5 minutes)
- Cache user profile (TTL: 1 minute)
- Invalidate on user action (deposit, withdrawal)

**2.4 Context Injection**
- Inject user context into AI prompts
- Inject product knowledge into AI prompts
- Keep context size manageable (token limits)

### Deliverables
- Product knowledge retrieval
- User context retrieval
- Context-aware AI responses
- Privacy filters (don't expose sensitive data unnecessarily)

### Risks & Mitigations
- **Risk**: Stale product information
- **Mitigation**: Short TTL, cache invalidation on product changes
- **Risk**: Privacy leaks in AI responses
- **Mitigation**: Explicit filtering, audit logs, redaction rules

---

## Phase 3: Tool System

### Goal
Enable Ganopa to perform actions, not just answer questions.

### Architecture Changes

**3.1 Tool Registry**
- Define tool interface (name, description, parameters, return type)
- Register tools at startup
- Tool discovery and validation

**3.2 Tool Categories**

**3.2.1 Read-Only Tools**
- `get_balance`: Retrieve user account balance
- `get_portfolio`: Get user positions
- `get_transaction_history`: List recent transactions
- `get_product_info`: Get product details
- `check_kyc_status`: Check user verification status

**3.2.2 Simulation Tools**
- `simulate_deposit`: Calculate deposit impact (no actual transaction)
- `simulate_withdrawal`: Calculate withdrawal impact
- `simulate_portfolio_allocation`: Show portfolio scenarios
- `calculate_fees`: Compute fees for an operation

**3.2.3 Action Tools (Phase 4)**
- `initiate_deposit`: Start deposit flow
- `initiate_withdrawal`: Start withdrawal flow
- `update_preferences`: Change user settings

**3.3 Tool Execution Engine**
- Parse AI tool calls from OpenAI response
- Validate tool parameters
- Execute tool with user context
- Format tool results for AI
- Handle tool errors gracefully

**3.4 Tool Result Formatting**
- Convert API responses to natural language
- Summarize large datasets
- Highlight important information

### Deliverables
- Tool registry and execution engine
- 5+ read-only tools
- 3+ simulation tools
- Tool result formatting
- Error handling for tool failures

### Risks & Mitigations
- **Risk**: AI calls wrong tool or with wrong parameters
- **Mitigation**: Strict parameter validation, tool descriptions, confirmation for critical actions
- **Risk**: Tool execution timeouts
- **Mitigation**: Timeout limits, async execution for long operations

---

## Phase 4: Memory & Context Management

### Goal
Enable multi-turn conversations with context retention.

### Architecture Changes

**4.1 Conversation State**
- Store conversation history per user
- Limit history length (last N messages)
- Compress old messages to save tokens

**4.2 Context Window Management**
- Track token usage per conversation
- Prune old messages when approaching limits
- Summarize old context instead of discarding

**4.3 User Preferences Memory**
- Remember user preferences (language, communication style)
- Store user-specific context (goals, risk tolerance)
- Update preferences based on user feedback

**4.4 Persistent Storage**
- Database for conversation history
- Index by user ID and timestamp
- Retention policy (delete after N days)

### Deliverables
- Conversation history storage
- Context window management
- User preference persistence
- Multi-turn conversation support

### Risks & Mitigations
- **Risk**: Token costs grow with conversation length
- **Mitigation**: Aggressive summarization, hard limits on history
- **Risk**: Privacy concerns with stored conversations
- **Mitigation**: Encryption at rest, user deletion rights, retention limits

---

## Phase 5: Safety & Compliance

### Goal
Ensure Ganopa operates within regulatory and safety boundaries.

### Architecture Changes

**5.1 Input Validation**
- Sanitize user inputs
- Detect and block malicious patterns
- Rate limiting per user
- Content moderation (inappropriate requests)

**5.2 Output Safety**
- Response validation before sending
- Block financial advice (regulatory compliance)
- Disclaimers for simulations
- Never commit to specific returns or guarantees

**5.3 Audit Trail**
- Log all user interactions
- Log all tool executions
- Log all AI responses
- Store logs in immutable storage
- Compliance export (GDPR, financial regulations)

**5.4 Access Control**
- Verify user permissions before tool execution
- KYC status checks before financial operations
- Role-based access (user, admin, support)
- Session validation

**5.5 Error Handling**
- Never expose internal errors to users
- Log errors with context
- Alert on repeated failures
- Graceful degradation

**5.6 Regulatory Compliance**
- Financial advice disclaimer
- Data protection (GDPR)
- Transaction limits enforcement
- AML/KYC checks before actions

### Deliverables
- Input/output validation system
- Comprehensive audit logging
- Access control layer
- Compliance checks
- Error handling and monitoring

### Risks & Mitigations
- **Risk**: Regulatory violations
- **Mitigation**: Legal review of prompts, explicit disclaimers, human review for sensitive operations
- **Risk**: Data breaches
- **Mitigation**: Encryption, access controls, regular security audits

---

## Phase 6: Onboarding & User Guidance

### Goal
Help users get started and guide them through Vancelian features.

### Architecture Changes

**6.1 Onboarding Flow**
- Detect new users
- Guide through account linking
- Explain available features
- Collect user preferences

**6.2 Feature Discovery**
- Suggest relevant features based on user profile
- Explain products in user's language
- Provide step-by-step guidance

**6.3 Help System**
- Context-aware help (what can I do now?)
- Product explanations
- FAQ integration
- Escalation to human support

### Deliverables
- Onboarding conversation flow
- Feature discovery prompts
- Help system integration
- User guidance tools

---

## Phase 7: Advanced Capabilities

### Goal
Add sophisticated agent behaviors.

### Architecture Changes

**7.1 Proactive Notifications**
- Alert users about important events (deposit received, withdrawal processed)
- Remind users about pending actions
- Suggest actions based on user behavior

**7.2 Multi-Modal Support**
- Handle images (receipts, documents)
- Process voice messages
- Support file uploads

**7.3 Planning & Goal Setting**
- Help users set financial goals
- Track progress toward goals
- Suggest actions to reach goals

**7.4 Integration with Other Services**
- Calendar integration (reminders)
- Email integration (notifications)
- External API integrations

### Deliverables
- Proactive notification system
- Multi-modal input processing
- Goal tracking and planning
- External service integrations

---

## Implementation Priorities

### Must-Have (MVP)
1. Phase 1: Backend connection
2. Phase 2: Basic domain knowledge (products, user balance)
3. Phase 3: Read-only tools (get_balance, get_product_info)
4. Phase 5: Basic safety (input validation, audit logs)

### Should-Have (V1)
5. Phase 3: Simulation tools
6. Phase 4: Conversation memory
7. Phase 5: Full compliance layer

### Nice-to-Have (V2+)
8. Phase 6: Onboarding
9. Phase 3: Action tools (with human approval)
10. Phase 7: Advanced capabilities

---

## Technical Architecture Overview

```
┌─────────────────┐
│  Telegram       │
│  (User)         │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Ganopa Bot Service            │
│  ┌───────────────────────────┐ │
│  │ Message Handler           │ │
│  │ - Parse Telegram update    │ │
│  │ - Extract user ID          │ │
│  └───────────┬───────────────┘ │
│              ▼                  │
│  ┌───────────────────────────┐ │
│  │ Authentication Layer       │ │
│  │ - Link Telegram → Vancelian │ │
│  │ - Get session token         │ │
│  └───────────┬───────────────┘ │
│              ▼                  │
│  ┌───────────────────────────┐ │
│  │ Context Manager            │ │
│  │ - Load user profile        │ │
│  │ - Load product catalog     │ │
│  │ - Load conversation history│ │
│  └───────────┬───────────────┘ │
│              ▼                  │
│  ┌───────────────────────────┐ │
│  │ AI Agent Engine            │ │
│  │ - Build prompt with context│ │
│  │ - Call OpenAI              │ │
│  │ - Parse tool calls         │ │
│  └───────────┬───────────────┘ │
│              ▼                  │
│  ┌───────────────────────────┐ │
│  │ Tool Executor              │ │
│  │ - Validate tool call       │ │
│  │ - Execute tool              │ │
│  │ - Format result            │ │
│  └───────────┬───────────────┘ │
│              ▼                  │
│  ┌───────────────────────────┐ │
│  │ Safety & Compliance         │ │
│  │ - Validate response         │ │
│  │ - Audit log                 │ │
│  │ - Check permissions         │ │
│  └───────────┬───────────────┘ │
│              ▼                  │
│  ┌───────────────────────────┐ │
│  │ Response Handler            │ │
│  │ - Format for Telegram       │ │
│  │ - Send message              │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Vancelian Backend APIs         │
│  - Auth API                     │
│  - User API                     │
│  - Product API                  │
│  - Transaction API              │
└─────────────────────────────────┘
```

---

## Key Design Principles

1. **Fail-Safe Defaults**: If backend is down, bot should still respond (with limitations)
2. **Privacy First**: Never expose sensitive data unless necessary
3. **Audit Everything**: All interactions logged for compliance
4. **Progressive Enhancement**: Start simple, add complexity gradually
5. **User Control**: Users can always opt out, delete data, get human support
6. **Regulatory Compliance**: Built-in, not bolted-on

---

## Success Metrics

- **Phase 1**: 100% of users can link accounts, 0 backend connection errors
- **Phase 2**: AI responses include relevant product info 90% of the time
- **Phase 3**: Users successfully use tools 95% of the time
- **Phase 4**: Multi-turn conversations maintain context 80% of the time
- **Phase 5**: 0 compliance violations, 100% audit coverage
- **Phase 6**: 80% of new users complete onboarding via bot
- **Phase 7**: User satisfaction score > 4.5/5

---

## Next Steps

1. Review and approve roadmap
2. Design Phase 1 API contracts
3. Set up backend API client library
4. Implement user linking flow
5. Test end-to-end: Telegram → Ganopa → Backend → Response


