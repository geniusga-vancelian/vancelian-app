import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/app_entry/domain/post_auth_sensitive_flow_policy.dart';

void main() {
  group('PostAuthSensitiveFlowPolicy.coldStartPolicy', () {
    test('setup PIN / OTP / passkey → forbiddenWithoutFullReauth', () {
      expect(
        PostAuthSensitiveFlowPolicy.coldStartPolicy(
          PostAuthSensitiveFlowKind.passcodeSetupFirstTime,
        ),
        PostAuthFlowColdStartPolicy.forbiddenWithoutFullReauth,
      );
      expect(
        PostAuthSensitiveFlowPolicy.coldStartPolicy(
          PostAuthSensitiveFlowKind.otpVerifySms,
        ),
        PostAuthFlowColdStartPolicy.forbiddenWithoutFullReauth,
      );
      expect(
        PostAuthSensitiveFlowPolicy.coldStartPolicy(
          PostAuthSensitiveFlowKind.passkeyEnrollment,
        ),
        PostAuthFlowColdStartPolicy.forbiddenWithoutFullReauth,
      );
    });

    test('unlock / secure gate → reenterThroughSecureGateOrLogin', () {
      expect(
        PostAuthSensitiveFlowPolicy.coldStartPolicy(
          PostAuthSensitiveFlowKind.passcodeUnlock,
        ),
        PostAuthFlowColdStartPolicy.reenterThroughSecureGateOrLogin,
      );
      expect(
        PostAuthSensitiveFlowPolicy.coldStartPolicy(
          PostAuthSensitiveFlowKind.secureGate,
        ),
        PostAuthFlowColdStartPolicy.reenterThroughSecureGateOrLogin,
      );
    });
  });

  group('PostAuthSensitiveFlowPolicy.tagsFor', () {
    test('passcode setup includes forbiddenToResumeAfterColdStart', () {
      final t = PostAuthSensitiveFlowPolicy.tagsFor(
        PostAuthSensitiveFlowKind.passcodeSetupFirstTime,
      );
      expect(t, contains(PostAuthFlowTag.forbiddenToResumeAfterColdStart));
      expect(t, contains(PostAuthFlowTag.resumableSameExecutionOnly));
    });
  });
}
