import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';

/// Réponse de l'API chat (contenu Markdown).
class ChatResponse {
  const ChatResponse({required this.content});
  final String content;

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      content: (json['content'] as String?) ?? '',
    );
  }
}

/// Envoie l'historique de messages à l'API chat et retourne la réponse assistant.
Future<ChatResponse> sendChatMessages(List<ChatMessagePayload> messages) async {
  final body = jsonEncode({
    'messages': messages.map((m) => {'role': m.role, 'content': m.content}).toList(),
  });
  final response = await http.post(
    Uri.parse(Config.chatUrl),
    headers: {'Content-Type': 'application/json'},
    body: body,
  );
  if (response.statusCode != 200) {
    final err = (jsonDecode(response.body) as Map<String, dynamic>?)?['error'] ?? response.body;
    throw ChatApiException(response.statusCode, err.toString());
  }
  final data = jsonDecode(response.body) as Map<String, dynamic>;
  return ChatResponse.fromJson(data);
}

class ChatMessagePayload {
  const ChatMessagePayload({required this.role, required this.content});
  final String role; // 'user' | 'assistant' | 'system'
  final String content;
}

class ChatApiException implements Exception {
  ChatApiException(this.statusCode, this.message);
  final int statusCode;
  final String message;
  @override
  String toString() => 'ChatApiException($statusCode): $message';
}
