/// Helpers partagés pour le flow swap LI.FI V1 (EVM — USDC, USDT, ETH).
class LifiSwapFlowFormat {
  LifiSwapFlowFormat._();

  static const v1Tokens = {'USDC', 'USDT', 'ETH'};

  static const evmChains = {'ethereum', 'arbitrum', 'base', 'polygon'};

  static const chainLabels = <String, String>{
    'ethereum': 'Ethereum',
    'arbitrum': 'Arbitrum',
    'base': 'Base',
    'polygon': 'Polygon',
  };

  static String chainLabel(String chain) => chainLabels[chain] ?? chain;

  static bool isV1Token(String symbol) => v1Tokens.contains(symbol.toUpperCase());

  static bool isEvmChain(String chain) => evmChains.contains(chain.toLowerCase());

  static List<String> filterEvmChains(List<String> chains) {
    return chains.where(isEvmChain).toList(growable: false);
  }

  static String defaultChainForAsset(String asset, List<String> chains) {
    final evm = filterEvmChains(chains);
    if (evm.isEmpty) return '';
    final sym = asset.toUpperCase();
    const preferred = <String, String>{
      'USDC': 'base',
      'USDT': 'base',
      'ETH': 'ethereum',
    };
    final pick = preferred[sym];
    if (pick != null && evm.contains(pick)) return pick;
    return evm.first;
  }

  static String formatCryptoAmount(double value) {
    if (value < 0.0001) return value.toStringAsExponential(2);
    String s;
    if (value < 1) {
      s = value.toStringAsFixed(8);
    } else {
      s = value.toStringAsFixed(6);
    }
    if (s.contains('.')) {
      s = s.replaceAll(RegExp(r'0+$'), '');
      s = s.replaceAll(RegExp(r'\.$'), '');
    }
    return s;
  }

  static String formatCryptoString(String raw) {
    final n = double.tryParse(raw.replaceAll(',', '.'));
    if (n == null) return raw;
    return formatCryptoAmount(n);
  }
}
