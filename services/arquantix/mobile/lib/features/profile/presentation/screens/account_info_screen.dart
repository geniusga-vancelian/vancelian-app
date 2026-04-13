import 'package:flutter/material.dart';

import '../../../../core/profile_identity_coordinator.dart';
import '../../../../core/profile_leading_preference.dart';
import '../../../security/passcode/data/session_service.dart';
import '../../../../design_system/design_system.dart';
import '../../data/mobile_app_profile.dart';

/// Informations du compte : données du client courant (person.profile_json via BFF).
class AccountInfoScreen extends StatefulWidget {
  const AccountInfoScreen({super.key});

  @override
  State<AccountInfoScreen> createState() => _AccountInfoScreenState();
}

class _AccountInfoScreenState extends State<AccountInfoScreen> {
  bool _loading = true;
  String? _error;
  MobileAppProfile? _profile;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    if (!forceRefresh) {
      final cached = ProfileIdentityCoordinator.instance.cachedProfile;
      if (cached != null) {
        if (!mounted) return;
        setState(() {
          _profile = cached;
          _loading = false;
          _error = null;
        });
        ProfileLeadingPreference.instance.loadFromBootstrapJson(cached.initials);
        return;
      }
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    final hasCred = await SessionService.instance.hasSessionCredentials();
    final p = await ProfileIdentityCoordinator.instance.loadAccountProfile(
      forceRefresh: forceRefresh,
      debugTag: 'AccountInfoScreen',
    );
    if (!mounted) return;
    if (p == null) {
      setState(() {
        _profile = null;
        _loading = false;
        _error = hasCred
            ? 'Impossible de charger le profil. Si le problème persiste, vérifiez '
                'que le compte client est bien lié à cette session (JWT).'
            : 'Session requise pour afficher le profil.';
      });
      return;
    }
    ProfileLeadingPreference.instance.loadFromBootstrapJson(p.initials);
    setState(() {
      _profile = p;
      _loading = false;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return PageSimpleNavBarTopTitlePageContent(
        pageTitle: 'Mon compte',
        content: const [
          SizedBox(height: AppSpacing.xxl),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }
    if (_error != null) {
      return PageSimpleNavBarTopTitlePageContent(
        pageTitle: 'Mon compte',
        content: [
          const SizedBox(height: AppSpacing.xl),
          Text(_error!, style: AppTypography.paragraph),
          const SizedBox(height: AppSpacing.lg),
          TextButton(
            onPressed: () => _load(forceRefresh: true),
            child: const Text('Réessayer'),
          ),
        ],
      );
    }

    final p = _profile!;
    final sections = <Widget>[];

    final personal = p.personal;
    if (personal != null) {
      final items = <SettingsListItem>[];
      if (personal.firstName != null) {
        items.add(SettingsListItem(title: 'Prénom', description: personal.firstName));
      }
      if (personal.lastName != null) {
        items.add(SettingsListItem(title: 'Nom', description: personal.lastName));
      }
      if (personal.dateOfBirth != null) {
        items.add(SettingsListItem(title: 'Date de naissance', description: personal.dateOfBirth));
      }
      if (personal.nationality != null) {
        items.add(SettingsListItem(title: 'Nationalité', description: personal.nationality));
      }
      if (items.isNotEmpty) {
        sections.add(_sectionTitleAndCard(
          title: 'Informations personnelles',
          showEdit: false,
          cardChildren: items,
        ));
      }
    }

    final address = p.address;
    if (address != null) {
      final items = <SettingsListItem>[];
      if (address.line1 != null) {
        items.add(SettingsListItem(title: 'Adresse', description: address.line1));
      }
      if (address.line2 != null) {
        items.add(SettingsListItem(title: 'Complément', description: address.line2));
      }
      if (address.postalCode != null) {
        items.add(SettingsListItem(title: 'Code postal', description: address.postalCode));
      }
      if (address.city != null) {
        items.add(SettingsListItem(title: 'Ville', description: address.city));
      }
      if (address.country != null) {
        items.add(SettingsListItem(title: 'Pays', description: address.country));
      }
      if (items.isNotEmpty) {
        sections.add(_sectionTitleAndCard(
          title: 'Adresse',
          showEdit: true,
          cardChildren: items,
        ));
      }
    }

    final identity = p.identity;
    if (identity != null) {
      final items = <SettingsListItem>[];
      if (identity.documentType != null) {
        items.add(SettingsListItem(title: 'Type de document', description: identity.documentType));
      }
      if (identity.documentNumberMasked != null) {
        items.add(SettingsListItem(title: 'Numéro', description: identity.documentNumberMasked));
      }
      if (identity.documentExpiry != null) {
        items.add(SettingsListItem(title: 'Date d\'expiration', description: identity.documentExpiry));
      }
      if (items.isNotEmpty) {
        sections.add(_sectionTitleAndCard(
          title: 'Pièce d\'identité',
          showEdit: false,
          cardChildren: items,
        ));
      }
    }

    final contact = p.contact;
    if (contact != null) {
      final items = <SettingsListItem>[];
      final contactEmail = p.displayEmailOrNull;
      if (contactEmail != null) {
        items.add(
          SettingsListItem(
            title: 'Email',
            description: contactEmail,
            trailing: SettingsActionButton(
              label: 'Edit',
              actionType: SettingsActionType.edit,
              onTap: () {},
            ),
          ),
        );
      }
      if (contact.phone != null) {
        items.add(
          SettingsListItem(
            title: 'Téléphone',
            description: contact.phone,
            trailing: SettingsActionButton(
              label: 'Edit',
              actionType: SettingsActionType.edit,
              onTap: () {},
            ),
          ),
        );
      }
      if (items.isNotEmpty) {
        sections.add(_sectionTitleAndCard(
          title: 'Contact',
          showEdit: false,
          cardChildren: items,
        ));
      }
    }

    final employment = p.employment;
    if (employment != null) {
      final items = <SettingsListItem>[];
      if (employment.employmentStatus != null) {
        items.add(SettingsListItem(
          title: 'Situation professionnelle',
          description: employment.employmentStatus,
        ));
      }
      if (employment.jobTitle != null) {
        items.add(SettingsListItem(title: 'Poste', description: employment.jobTitle));
      }
      if (employment.workSector != null) {
        items.add(SettingsListItem(title: 'Secteur', description: employment.workSector));
      }
      if (employment.employerName != null) {
        items.add(SettingsListItem(title: 'Employeur', description: employment.employerName));
      }
      if (items.isNotEmpty) {
        sections.add(_sectionTitleAndCard(
          title: 'Activité professionnelle',
          showEdit: false,
          cardChildren: items,
        ));
      }
    }

    final financial = p.financial;
    if (financial != null) {
      final items = <SettingsListItem>[];
      if (financial.annualIncomeRange != null) {
        items.add(SettingsListItem(
          title: 'Revenus annuels (fourchette)',
          description: financial.annualIncomeRange,
        ));
      }
      if (financial.netWorthRange != null) {
        items.add(SettingsListItem(
          title: 'Patrimoine (fourchette)',
          description: financial.netWorthRange,
        ));
      }
      if (financial.sourceOfWealth != null) {
        items.add(SettingsListItem(
          title: 'Origine des fonds',
          description: financial.sourceOfWealth,
        ));
      }
      if (items.isNotEmpty) {
        sections.add(_sectionTitleAndCard(
          title: 'Profil financier',
          showEdit: false,
          cardChildren: items,
        ));
      }
    }

    final legal = p.legal;
    if (legal != null) {
      final items = <SettingsListItem>[];
      if (legal.termsAccepted != null) {
        items.add(SettingsListItem(title: 'Conditions générales', description: legal.termsAccepted));
      }
      if (legal.infoTrueAndAccurate != null) {
        items.add(SettingsListItem(
          title: 'Exactitude des informations',
          description: legal.infoTrueAndAccurate,
        ));
      }
      if (legal.complianceUsageAck != null) {
        items.add(SettingsListItem(
          title: 'Usage conforme',
          description: legal.complianceUsageAck,
        ));
      }
      if (legal.notUsPerson != null) {
        items.add(SettingsListItem(
          title: 'Non résident US',
          description: legal.notUsPerson,
        ));
      }
      if (items.isNotEmpty) {
        sections.add(_sectionTitleAndCard(
          title: 'Déclarations',
          showEdit: false,
          cardChildren: items,
        ));
      }
    }

    final accountItems = <SettingsListItem>[];
    if (p.jurisdiction != null) {
      accountItems.add(SettingsListItem(title: 'Juridiction', description: p.jurisdiction));
    }
    if (p.kycStatus != null) {
      accountItems.add(SettingsListItem(title: 'KYC', description: p.kycStatus));
    }
    if (p.clientStatus != null) {
      accountItems.add(SettingsListItem(title: 'Statut compte', description: p.clientStatus));
    }
    if (p.referenceCurrency != null) {
      accountItems.add(SettingsListItem(
        title: 'Devise de référence',
        description: p.referenceCurrency,
      ));
    }
    if (accountItems.isNotEmpty) {
      sections.add(_sectionTitleAndCard(
        title: 'Compte',
        showEdit: false,
        cardChildren: accountItems,
      ));
    }

    if (sections.isEmpty) {
      sections.add(
        Padding(
          padding: const EdgeInsets.only(top: AppSpacing.xl),
          child: Text(
            'Aucune information de profil enregistrée pour le moment.',
            style: AppTypography.paragraph.copyWith(color: AppColors.textSecondary),
          ),
        ),
      );
    }

    final spaced = <Widget>[];
    for (var i = 0; i < sections.length; i++) {
      spaced.add(sections[i]);
      if (i < sections.length - 1) {
        spaced.add(const SizedBox(height: AppSpacing.xxl));
      }
    }
    spaced.add(const SizedBox(height: AppSpacing.xxl));

    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Mon compte',
      content: spaced,
    );
  }

  Widget _sectionTitleAndCard({
    required String title,
    required bool showEdit,
    required List<SettingsListItem> cardChildren,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (showEdit)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              AppSectionTitle2(title),
              SettingsActionButton(
                label: 'Edit',
                actionType: SettingsActionType.edit,
                onTap: () {},
              ),
            ],
          )
        else
          AppSectionTitle2(title),
        const SizedBox(height: AppSpacing.sm),
        SettingsCard(children: cardChildren),
      ],
    );
  }
}
