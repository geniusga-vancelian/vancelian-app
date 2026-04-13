import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/home/application/partial_registration_dashboard_rules.dart';
import 'package:arquantix_news/features/profile/data/mobile_app_profile.dart';
import 'package:arquantix_news/features/wallet/domain/models/cash_data.dart';

CashData _cashWithEurAccount({double balance = 0}) {
  return CashData(
    client: const CashClient(
      id: 'c1',
      email: 'a@b.c',
      status: 'active',
      kycStatus: 'verified',
    ),
    cashAccount: CashAccount(
      accountId: 'acc1',
      currency: 'EUR',
      availableBalance: balance,
      pendingBalance: 0,
    ),
  );
}

void main() {
  group('hasEuroCashAccount', () {
    test('false when cash null', () {
      expect(hasEuroCashAccount(null), false);
    });
    test('false when cash_account absent', () {
      final d = CashData(
        client: const CashClient(
          id: 'c1',
          email: 'a@b.c',
          status: 'active',
          kycStatus: 'verified',
        ),
      );
      expect(hasEuroCashAccount(d), false);
    });
    test('true when EUR account exists even if balance zero', () {
      expect(hasEuroCashAccount(_cashWithEurAccount(balance: 0)), true);
    });
    test('false when currency is not EUR', () {
      final d = CashData(
        client: const CashClient(
          id: 'c1',
          email: 'a@b.c',
          status: 'active',
          kycStatus: 'verified',
        ),
        cashAccount: CashAccount(
          accountId: 'acc1',
          currency: 'USD',
          availableBalance: 10,
          pendingBalance: 0,
        ),
      );
      expect(hasEuroCashAccount(d), false);
    });
  });

  group('shouldUsePreDepositActivationHeader', () {
    test('PARTIAL + compte EUR : forcer header standard', () {
      final p = MobileAppProfile(
        initials: 'A',
        email: 'a@b.c',
        clientStatus: 'PARTIAL',
      );
      expect(
        shouldUsePreDepositActivationHeader(
          basePreDepositConditionsMet: true,
          profile: p,
          cash: _cashWithEurAccount(),
        ),
        false,
      );
    });

    test('PARTIAL + pas de compte EUR : garder pré-dépôt si base ok', () {
      final p = MobileAppProfile(
        initials: 'A',
        email: 'a@b.c',
        clientStatus: 'PARTIAL',
      );
      expect(
        shouldUsePreDepositActivationHeader(
          basePreDepositConditionsMet: true,
          profile: p,
          cash: null,
        ),
        true,
      );
    });

    test('ACTIVE + compte EUR : inchangé si base ok (pas PARTIAL)', () {
      final p = MobileAppProfile(
        initials: 'A',
        email: 'a@b.c',
        clientStatus: 'ACTIVE',
      );
      expect(
        shouldUsePreDepositActivationHeader(
          basePreDepositConditionsMet: true,
          profile: p,
          cash: _cashWithEurAccount(),
        ),
        true,
      );
    });

    test('base false : jamais pré-dépôt', () {
      final p = MobileAppProfile(
        initials: 'A',
        email: 'a@b.c',
        clientStatus: 'PARTIAL',
      );
      expect(
        shouldUsePreDepositActivationHeader(
          basePreDepositConditionsMet: false,
          profile: p,
          cash: null,
        ),
        false,
      );
    });
  });

  group('shouldShowPartialRegistrationDashboardExperience', () {
    test('PARTIAL sans cash EUR', () {
      final p = MobileAppProfile(
        initials: 'A',
        email: 'a@b.c',
        clientStatus: 'PARTIAL',
      );
      expect(
        shouldShowPartialRegistrationDashboardExperience(profile: p, cash: null),
        true,
      );
    });
    test('PARTIAL avec compte EUR', () {
      final p = MobileAppProfile(
        initials: 'A',
        email: 'a@b.c',
        clientStatus: 'PARTIAL',
      );
      expect(
        shouldShowPartialRegistrationDashboardExperience(
          profile: p,
          cash: _cashWithEurAccount(),
        ),
        false,
      );
    });
  });

  group('resolveHomeDashboardOrchestrationMode', () {
    test('mappe le booléen header', () {
      expect(
        resolveHomeDashboardOrchestrationMode(
          usePreDepositActivationHeader: true,
        ),
        HomeDashboardOrchestrationMode.preDepositActivation,
      );
      expect(
        resolveHomeDashboardOrchestrationMode(
          usePreDepositActivationHeader: false,
        ),
        HomeDashboardOrchestrationMode.standard,
      );
    });
  });
}
