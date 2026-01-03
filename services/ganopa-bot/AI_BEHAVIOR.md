# Ganopa AI Behavior - Design Document

## Overview

Ganopa is a professional AI assistant specialized in fintech, designed for Telegram interactions with a focus on accuracy, conciseness, and helpfulness.

## System Prompt

The system prompt is defined in `app/ai_prompt.py` and includes:

- **Role**: Professional fintech assistant
- **Tone**: Professional yet friendly
- **Language**: Auto-detection (French default)
- **Length**: Maximum 200 words (enforced via max_tokens)
- **Accuracy**: Only provide certain information, avoid hallucinations
- **Format**: Clear, structured responses

## Implementation

The OpenAI call function is in `app/ai_service.py` with:

- Robust error handling
- Comprehensive logging
- Token limits (300 tokens = ~200 words)
- Lower temperature (0.3) for consistency
- User-friendly error messages

## Example Input/Output

### Example 1: French Question (Fintech)

**Input:**
```
Comment fonctionne un virement SEPA ?
```

**Expected Output:**
```
Un virement SEPA (Single Euro Payments Area) permet de transférer des fonds entre comptes bancaires dans la zone SEPA (UE, EEE, Suisse, Monaco, etc.).

**Fonctionnement :**
- Le virement est initié par l'émetteur
- Les fonds sont débités du compte source
- Le crédit arrive généralement sous 1 jour ouvrable (virement standard) ou le jour même (virement instantané)

**Informations requises :**
- IBAN du bénéficiaire
- BIC (optionnel pour virements intra-UE)
- Montant et devise
- Référence/motif

Les frais varient selon la banque et le type de virement. Pour des montants importants ou des questions spécifiques, je recommande de consulter votre conseiller bancaire.
```

### Example 2: English Question (General)

**Input:**
```
What is a payment gateway?
```

**Expected Output:**
```
A payment gateway is a technology service that processes online payments between merchants and customers. It acts as a bridge between the merchant's website and the payment processor.

**Key functions:**
- Encrypts payment data for security
- Validates transactions
- Routes payments to appropriate banks
- Handles authorization and settlement

**Common examples:** Stripe, PayPal, Square, Adyen

For fintech applications, choosing the right payment gateway depends on factors like transaction volume, geographic coverage, and supported payment methods.
```

### Example 3: Unknown Information (Hallucination Prevention)

**Input:**
```
Quel est le taux d'intérêt actuel pour un prêt immobilier en France ?
```

**Expected Output:**
```
Je ne peux pas vous fournir les taux d'intérêt actuels car ils changent régulièrement et dépendent de nombreux facteurs (durée, profil emprunteur, type de bien, etc.).

**Je recommande de :**
- Consulter plusieurs établissements bancaires
- Utiliser des comparateurs en ligne
- Contacter un courtier en crédit immobilier

Les taux varient généralement entre 3% et 5% selon les conditions, mais seul un établissement financier peut vous donner une proposition précise adaptée à votre situation.
```

### Example 4: Too Long Question (Truncation)

**Input:**
```
Peux-tu m'expliquer en détail toute l'histoire de la finance depuis l'antiquité jusqu'à aujourd'hui avec tous les détails sur chaque période, les innovations, les crises, les personnages importants, etc. ?
```

**Expected Output:**
```
C'est un sujet très vaste ! Je vais vous donner un aperçu structuré :

**Périodes clés :**
- Antiquité : Premiers systèmes de crédit (Mésopotamie, Grèce)
- Moyen Âge : Développement des banques (Italie, Flandre)
- Renaissance : Bourses de commerce, lettres de change
- 17e-18e siècles : Banques centrales, compagnies des Indes
- 19e siècle : Industrialisation, expansion bancaire
- 20e siècle : Crise de 1929, Bretton Woods, dérégulation
- 21e siècle : Fintech, crypto-monnaies, régulation post-2008

**Innovations majeures :**
- Monnaie fiduciaire, crédit, actions, obligations, produits dérivés

Pour approfondir un aspect spécifique, dites-moi ce qui vous intéresse le plus !
```

## Integration

To use the new AI service in `main.py`:

```python
from .ai_service import call_openai

# In process_telegram_update():
reply = call_openai(text, update_id=update.get("update_id"), chat_id=chat_id)
send_telegram_message(chat_id, reply, update_id=update.get("update_id"))
```

## Configuration

- **Model**: `gpt-4o-mini` (configurable via `OPENAI_MODEL` env var)
- **Temperature**: 0.3 (low for consistency)
- **Max tokens**: 300 (enforced in function)
- **Timeout**: 30 seconds

## Safety Features

1. **Hallucination prevention**: Explicit instructions to only provide certain information
2. **Length limits**: Max tokens enforced
3. **Error handling**: User-friendly messages for all error cases
4. **Logging**: Comprehensive logging for debugging and monitoring
5. **Input validation**: Empty/invalid input handling


