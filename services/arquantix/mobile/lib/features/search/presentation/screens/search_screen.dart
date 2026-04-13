import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../../design_system/design_system.dart';
import '../../data/chat_api.dart';

/// Message affiché dans la conversation.
class _ChatMessage {
  const _ChatMessage({required this.role, required this.content});
  final String role; // 'user' | 'assistant'
  final String content;
}

/// Page recherche : interface type ChatGPT avec agent conversationnel (OpenAI, réponses Markdown).
/// [onBack] : si fourni, le bouton back appelle ce callback (ex. retour à l'accueil depuis le shell).
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key, this.onBack});

  final VoidCallback? onBack;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final List<_ChatMessage> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onInputChanged);
  }

  void _onInputChanged() => setState(() {});

  @override
  void dispose() {
    _controller.removeListener(_onInputChanged);
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _loading) return;

    _controller.clear();
    setState(() {
      _error = null;
      _messages.add(_ChatMessage(role: 'user', content: text));
      _loading = true;
    });

    _scrollToBottom();

    final history = _messages.map((m) => ChatMessagePayload(role: m.role, content: m.content)).toList();

    try {
      final response = await sendChatMessages(history);
      if (!mounted) return;
      setState(() {
        _messages.add(_ChatMessage(role: 'assistant', content: response.content));
        _loading = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e is ChatApiException ? e.message : e.toString();
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.cardBackground,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new),
          onPressed: () {
            if (widget.onBack != null) {
              widget.onBack!();
            } else {
              Navigator.of(context).pop();
            }
          },
        ),
        title: const Text('Search'),
        titleTextStyle: AppTypography.appBarTitle,
        backgroundColor: Colors.transparent,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        flexibleSpace: _buildBlurAppBarBackground(),
        actions: [
          IconButton(icon: const Icon(Icons.edit_outlined), onPressed: () {}),
          IconButton(icon: const Icon(Icons.more_vert), onPressed: () {}),
        ],
      ),
      body: Stack(
        children: [
          Column(
            children: [
              SizedBox(height: MediaQuery.paddingOf(context).top + kToolbarHeight),
              Expanded(
                child: _messages.isEmpty ? _buildEmptyState() : _buildMessageList(),
              ),
              if (_error != null) _buildErrorBanner(),
              SizedBox(height: _kInputBarHeight + MediaQuery.paddingOf(context).bottom),
            ],
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(
              top: false,
              child: _buildInputBar(),
            ),
          ),
        ],
      ),
    );
  }

  /// Header avec blur et base blanche (frosted glass).
  Widget _buildBlurAppBarBackground() {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.75),
          ),
        ),
      ),
    );
  }

  /// Tags proposés (mock). Sera remplacé par la base de données plus tard.
  static const List<String> _suggestedTags = [
    'Marché actions',
    'Portfolio',
    'Gestion du risque',
    'Épargne retraite',
    'Diversification',
    'Performance',
  ];

  Widget _buildEmptyState() {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl),
          child: Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.sizeOf(context).width * 0.75,
                minHeight: constraints.maxHeight,
              ),
              child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.max,
              children: [
                SvgPicture.asset(
                  'assets/logo-black-icon.svg',
                  width: 56,
                  height: 56,
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'Bonjour Gael, comment puis-je vous aider aujourd\'hui ?',
                  style: AppTypography.welcomeTitle,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'Vous pouvez choisir parmi une des catégories suivantes et vous laisser guider pas à pas.',
                  style: AppTypography.paragraph.copyWith(color: AppColors.textSecondary),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.sm),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 6,
                  runSpacing: 0,
                  children: _suggestedTags
                      .map((tag) => AppSuggestionChip(
                            label: tag,
                            onPressed: () {
                              _controller.text = tag;
                              _sendMessage();
                            },
                          ))
                      .toList(),
                ),
              ],
            ),
            ),
          ),
        );
      },
    );
  }

  static const Duration _loaderToMessageDuration = Duration(milliseconds: 100);
  static const double _kInputBarHeight = 72;

  Widget _buildMessageList() {
    final itemCount = _messages.length + (_loading ? 1 : 0);
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        top: AppSpacing.md,
        bottom: AppSpacing.md + _kInputBarHeight,
      ),
      itemCount: itemCount,
      itemBuilder: (context, index) {
        final isLastSlot = index == itemCount - 1;
        if (isLastSlot) {
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.lg),
            child: AnimatedSwitcher(
              duration: _loaderToMessageDuration,
              switchInCurve: Curves.easeOut,
              switchOutCurve: Curves.easeIn,
              transitionBuilder: (Widget child, Animation<double> animation) {
                return FadeTransition(opacity: animation, child: child);
              },
              child: _loading
                  ? _buildTypingDots(key: const ValueKey<String>('typing'))
                  : KeyedSubtree(
                      key: ValueKey<String>(_messages.last.content),
                      child: _buildAssistantBubble(_messages.last),
                    ),
            ),
          );
        }
        final msg = _messages[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.lg),
          child: msg.role == 'user' ? _buildUserBubble(msg) : _buildAssistantBubble(msg),
        );
      },
    );
  }

  Widget _buildUserBubble(_ChatMessage msg) {
    return Align(
      alignment: Alignment.centerRight,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.82),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.userMessageBubble,
            borderRadius: BorderRadius.circular(AppRadius.bubble),
          ),
          child: Text(msg.content, style: AppTypography.chatBody),
        ),
      ),
    );
  }

  Widget _buildAssistantBubble(_ChatMessage msg) {
    return Align(
      alignment: Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.92),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildShareMessageBar(msg.content),
            MarkdownBody(
              data: msg.content,
              selectable: true,
              styleSheet: _chatGptMarkdownStyleSheet(context),
              fitContent: true,
            ),
          ],
        ),
      ),
    );
  }

  /// Barre « Partager le message » type ChatGPT.
  Widget _buildShareMessageBar(String content) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          Clipboard.setData(ClipboardData(text: content));
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: const Text('Message copié'),
                duration: const Duration(seconds: 2),
                behavior: SnackBarBehavior.floating,
              ),
            );
          }
        },
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Padding(
          padding: const EdgeInsets.only(right: AppSpacing.sm, bottom: AppSpacing.sm),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Partager le message',
                style: AppTypography.meta.copyWith(fontSize: 14),
              ),
              const SizedBox(width: AppSpacing.xs),
              Icon(Icons.arrow_forward_ios, size: 12, color: AppColors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }

  /// Style Markdown type ChatGPT : lecture claire, tableaux épurés, titres et espacements.
  /// bodyStyle et headingStyle = Inter.
  MarkdownStyleSheet _chatGptMarkdownStyleSheet(BuildContext context) {
    const bodyColor = AppColors.textPrimary;
    final bodyStyle = AppTypography.chatBody;
    final headingStyle = AppTypography.titleLarge.copyWith(
      color: bodyColor,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.3,
      height: 1.35,
    );
    return MarkdownStyleSheet(
      p: bodyStyle,
      pPadding: const EdgeInsets.only(bottom: 12),
      strong: bodyStyle.copyWith(fontWeight: FontWeight.w700),
      em: bodyStyle.copyWith(fontStyle: FontStyle.italic),
      h1: headingStyle.copyWith(fontSize: 22),
      h1Padding: const EdgeInsets.only(top: 16, bottom: 8),
      h2: headingStyle.copyWith(fontSize: 18),
      h2Padding: const EdgeInsets.only(top: 14, bottom: 6),
      h3: headingStyle.copyWith(fontSize: 16),
      h3Padding: const EdgeInsets.only(top: 12, bottom: 4),
      h4: headingStyle.copyWith(fontSize: 15),
      h4Padding: const EdgeInsets.only(top: 10, bottom: 4),
      blockSpacing: 14,
      listIndent: 28,
      listBullet: bodyStyle,
      listBulletPadding: const EdgeInsets.only(right: 8),
      blockquote: bodyStyle.copyWith(color: AppColors.textSecondary),
      blockquotePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      blockquoteDecoration: BoxDecoration(
        border: Border(left: BorderSide(color: AppColors.border, width: 4)),
        color: AppColors.navBarActivePill,
      ),
      code: bodyStyle.copyWith(
        fontFamily: 'monospace',
        fontSize: 14,
        backgroundColor: AppColors.navBarActivePill,
      ),
      codeblockPadding: const EdgeInsets.all(14),
      codeblockDecoration: BoxDecoration(
        color: AppColors.navBarActivePill,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: AppColors.border),
      ),
      horizontalRuleDecoration: BoxDecoration(
        border: Border(top: BorderSide(color: AppColors.border, width: 1)),
      ),
      a: bodyStyle.copyWith(color: AppColors.accent, decoration: TextDecoration.underline),
      // Tableaux type ChatGPT : uniquement lignes horizontales (pas de délimitation verticale).
      tableHead: bodyStyle.copyWith(fontWeight: FontWeight.w700, fontSize: 14),
      tableBody: bodyStyle.copyWith(fontSize: 14),
      tablePadding: const EdgeInsets.only(bottom: 16),
      tableCellsPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      tableBorder: TableBorder(
        top: BorderSide.none,
        bottom: BorderSide(color: AppColors.border, width: 1),
        left: BorderSide.none,
        right: BorderSide.none,
        horizontalInside: BorderSide(color: AppColors.border, width: 1),
        verticalInside: BorderSide.none,
      ),
      // FlexColumnWidth évite le wrap Scrollbar+SingleChildScrollView : plus de scrollbar qui passe par-dessus le tableau.
      tableColumnWidth: const FlexColumnWidth(1),
    );
  }

  /// Loader 3 points animés (typing indicator).
  Widget _buildTypingDots({Key? key}) {
    return Align(
      key: key,
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.lg),
        child: const _TypingDotsAnimated(),
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
      color: AppColors.errorBackground,
      child: Text(
        _error!,
        style: AppTypography.meta.copyWith(color: AppColors.errorText),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }

  static const double _kInputSingleLineHeight = 44;

  Widget _buildInputBar() {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.fromLTRB(AppSpacing.sm, AppSpacing.sm, AppSpacing.sm, AppSpacing.sm + 8),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Colors.white.withValues(alpha: 0.0),
                Colors.white.withValues(alpha: 0.5),
                Colors.white.withValues(alpha: 0.85),
              ],
              stops: const [0.0, 0.4, 1.0],
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _buildPlusButton(),
              const SizedBox(width: AppSpacing.sm),
              Expanded(child: _buildInputPill()),
            ],
          ),
        ),
      ),
    );
  }

  /// Bouton "+" type ChatGPT : même fond gris que l’input, "+" simple non entouré. Ouvre la modale pièces jointes.
  Widget _buildPlusButton() {
    return SizedBox(
      width: _kInputSingleLineHeight,
      height: _kInputSingleLineHeight,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => ChatAttachmentModal.show(context),
          borderRadius: BorderRadius.circular(_kInputSingleLineHeight / 2),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.chatInputBg,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(
              Icons.add,
              size: 24,
              color: AppColors.textPrimary,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInputPill() {
    final hasText = _controller.text.trim().isNotEmpty;
    return Container(
      constraints: const BoxConstraints(minHeight: _kInputSingleLineHeight),
      decoration: BoxDecoration(
        color: AppColors.chatInputBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: 'Poser une question',
                hintStyle: AppTypography.chatBody.copyWith(color: AppColors.chatInputHint),
                filled: true,
                fillColor: Colors.transparent,
                isDense: true,
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                contentPadding: const EdgeInsets.fromLTRB(AppSpacing.lg, 11, AppSpacing.sm, 12),
              ),
              style: AppTypography.chatBody,
              maxLines: 4,
              minLines: 1,
              textInputAction: TextInputAction.newline,
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 6, bottom: 6, top: 6),
            child: _buildSendButton(hasContent: hasText),
          ),
        ],
      ),
    );
  }

  Widget _buildSendButton({required bool hasContent}) {
    const double size = 32.0;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: hasContent && !_loading ? _sendMessage : null,
        borderRadius: BorderRadius.circular(size / 2),
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: hasContent ? AppColors.textPrimary : AppColors.chatInputHint.withValues(alpha: 0.4),
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Icon(
            Icons.arrow_upward_rounded,
            size: 20,
            color: hasContent ? Colors.white : Colors.white70,
          ),
        ),
      ),
    );
  }
}

/// Trois points animés (rebond en séquence) pour le chargement.
class _TypingDotsAnimated extends StatefulWidget {
  const _TypingDotsAnimated();

  @override
  State<_TypingDotsAnimated> createState() => _TypingDotsAnimatedState();
}

class _TypingDotsAnimatedState extends State<_TypingDotsAnimated>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const dotSize = 8.0;
    const spacing = 6.0;
    const color = AppColors.textSecondary;
    return SizedBox(
      height: 24,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(3, (i) {
          final delay = i * 0.2;
          return AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final t = (_controller.value + delay) % 1.0;
              final s = t < 0.5 ? 2 * t : 2 * (1 - t);
              final scaleDot = 0.6 + 0.4 * s;
              return Padding(
                padding: EdgeInsets.only(right: i < 2 ? spacing : 0),
                child: Transform.scale(
                  scale: scaleDot,
                  child: Container(
                    width: dotSize,
                    height: dotSize,
                    decoration: const BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              );
            },
          );
        }),
      ),
    );
  }
}
