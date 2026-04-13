export type InfoItem = { title: string; body: string };

export type SidebarBullet = { emoji: string; text: string };

export type RegistrationSlideData = {
  /** Titre de section (ex. « 1. Identification personnelle ») */
  sectionTitle: string;
  intro: string;
  infoItems: InfoItem[];
  sidebarTitle: string;
  /** Ligne mise en avant sous le titre encadré */
  sidebarLead?: string;
  sidebarBullets: SidebarBullet[];
  /** Bloc optionnel de « tags » (slide 3) */
  tags?: string[];
  /** Paragraphe d’enjeu sous les tags */
  sidebarNote?: string;
  /** Décoration optionnelle (ex. slide résidence) */
  sidebarEmoji?: string;
};

export const REGISTRATION_DECK_TITLE = 'Registration chez Vancelian';

export const registrationSlides: RegistrationSlideData[] = [
  {
    sectionTitle: '1. Identification personnelle',
    intro:
      "Premier niveau de vérification : confirmer l'identité réelle du client avant l'ouverture effective du parcours d'investissement.",
    infoItems: [
      {
        title: 'État civil',
        body: "Nom, prénom, date de naissance, nationalité et parfois pays d'émission de la pièce d'identité.",
      },
      {
        title: 'Document officiel',
        body: "Passeport ou carte d'identité, avec contrôle d'authenticité et de validité.",
      },
      {
        title: 'Vérification biométrique',
        body: 'Selfie, contrôle de présence ou matching photo/document selon le niveau de risque.',
      },
    ],
    sidebarTitle: 'Pourquoi Vancelian le demande',
    sidebarLead:
      'Résultat attendu : le client est identifiable, vérifié et éligible à poursuivre l’inscription.',
    sidebarBullets: [
      { emoji: '🪪', text: "Empêcher l'usurpation d'identité et la fraude à l'entrée." },
      { emoji: '', text: 'Satisfaire les obligations de conformité avant toute relation d’affaires.' },
      { emoji: '', text: 'Créer un compte rattaché à une personne physique clairement identifiée.' },
    ],
  },
  {
    sectionTitle: '2. Coordonnées & communication',
    intro:
      'Deuxième bloc : disposer de canaux fiables pour sécuriser l’accès au compte et communiquer avec le client tout au long de la relation.',
    infoItems: [
      {
        title: 'E-mail personnel',
        body: 'Utilisé comme identifiant, canal d’activation et support des communications opérationnelles ou réglementaires.',
      },
      {
        title: 'Numéro de mobile',
        body: 'Permet les vérifications OTP, la sécurisation des connexions et la confirmation de certaines actions sensibles.',
      },
      {
        title: 'Validation des coordonnées',
        body: 'Contrôle de la disponibilité réelle des canaux avant accès complet à la plateforme.',
      },
    ],
    sidebarTitle: 'Rôle dans le parcours',
    sidebarLead:
      'Ce bloc ne sert pas uniquement à contacter le client : il contribue directement à la sécurité du compte et à la fiabilité du parcours d’onboarding.',
    sidebarBullets: [
      { emoji: '📱', text: 'Activer le compte en toute sécurité.' },
      { emoji: '', text: 'Notifier le client sur les opérations, confirmations et alertes.' },
      { emoji: '', text: 'Maintenir une relation conforme et traçable.' },
    ],
  },
  {
    sectionTitle: '3. Résidence & rattachement réglementaire',
    intro:
      'Ce bloc permet de déterminer dans quelle juridiction le client réside et quelles règles de conformité, de fiscalité ou de distribution s’appliquent.',
    infoItems: [
      {
        title: 'Adresse de résidence',
        body: 'Adresse complète, ville, code postal, pays de résidence principale et parfois justificatif de domicile.',
      },
      {
        title: 'Résidence fiscale',
        body: 'Pays de rattachement fiscal et éléments complémentaires si plusieurs juridictions sont concernées.',
      },
      {
        title: 'Restrictions pays',
        body: 'Contrôle d’éligibilité par marché, sanctions, restrictions réglementaires ou limitations de distribution.',
      },
    ],
    sidebarTitle: 'Ce que cela permet',
    tags: ['Éligibilité marché', 'Filtrage pays', 'Conformité fiscale', 'Règles locales'],
    sidebarNote:
      'Enjeu clé : Vancelian ne peut pas proposer le même parcours ni les mêmes produits à tous les pays ; la résidence pilote donc le cadre de distribution.',
    sidebarBullets: [],
    sidebarEmoji: '🏠',
  },
  {
    sectionTitle: '4. Profil financier',
    intro:
      'Le bloc financier vise à comprendre la capacité économique du client et la cohérence future de son activité sur la plateforme.',
    infoItems: [
      {
        title: 'Situation professionnelle',
        body: 'Profession, statut, employeur ou secteur d’activité pour contextualiser la source des revenus.',
      },
      {
        title: 'Capacité financière',
        body: 'Revenus, niveau d’épargne, patrimoine ou fourchettes permettant d’évaluer la solidité économique du client.',
      },
      {
        title: 'Cohérence des flux',
        body: 'Première base d’analyse entre profil déclaré et comportements financiers observés par la suite.',
      },
    ],
    sidebarTitle: 'Finalité opérationnelle',
    sidebarLead:
      'À ce stade, il ne s’agit pas encore de recommander un produit : on établit d’abord la base économique et de conformité du client.',
    sidebarBullets: [
      { emoji: '💰', text: "Vérifier que l'activité future semble cohérente avec les moyens du client." },
      { emoji: '', text: 'Préparer les contrôles renforcés si montants ou comportements paraissent atypiques.' },
      { emoji: '', text: 'Compléter la vision globale du dossier avant mise à disposition des produits.' },
    ],
  },
  {
    sectionTitle: '5. Profil investisseur & rapport d’adéquation',
    intro:
      'Dernier bloc : qualifier les objectifs d’investissement, le niveau de risque acceptable et les connaissances financières afin de déterminer ce qui est adapté au client.',
    infoItems: [
      {
        title: 'Objectifs & horizon',
        body: 'Recherche de rendement, croissance, préservation du capital, horizon court, moyen ou long terme.',
      },
      {
        title: 'Appétence au risque',
        body: 'Capacité à accepter la volatilité, les pertes temporaires et les arbitrages entre sécurité et performance.',
      },
      {
        title: 'Connaissances financières',
        body: 'Questions sur l’expérience d’investissement, la compréhension des produits et le niveau de familiarité avec les risques.',
      },
    ],
    sidebarTitle: 'Ce que produit ce bloc',
    sidebarLead:
      'Point clé : le profil investisseur complète le KYC classique : il ne dit pas seulement si le client peut entrer, mais aussi quel type d’offre lui convient.',
    sidebarBullets: [
      { emoji: '📊', text: 'Un profil investisseur structuré et exploitable.' },
      { emoji: '', text: 'Un cadre de recommandation compatible avec le niveau de connaissance du client.' },
      { emoji: '', text: 'Un rapport d’adéquation justifiant pourquoi une offre ou une allocation est pertinente.' },
    ],
  },
];
