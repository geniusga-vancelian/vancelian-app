/// Compte source éligible pour un swap LI.FI.
class LifiSwapSourceAccount {
  const LifiSwapSourceAccount({
    required this.asset,
    required this.label,
    required this.chain,
    required this.balance,
    this.logoUrl,
  });

  final String asset;
  final String label;
  final String chain;
  final double balance;
  final String? logoUrl;
}
