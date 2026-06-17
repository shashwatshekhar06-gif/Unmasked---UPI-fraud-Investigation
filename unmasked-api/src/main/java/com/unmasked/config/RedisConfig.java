package com.unmasked.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.PatternTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

@Configuration
public class RedisConfig {

    @Bean
    RedisMessageListenerContainer container(RedisConnectionFactory connectionFactory,
                                            MessageListenerAdapter listenerAdapter) {
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        // subscribe to all case WebSocket channels: unmasked:ws:*
        container.addMessageListener(listenerAdapter, new PatternTopic("unmasked:ws:*"));
        return container;
    }

    @Bean
    MessageListenerAdapter listenerAdapter(WebSocketEventForwarder forwarder) {
        return new MessageListenerAdapter(forwarder, "handleMessage");
    }

    @Component
    public static class WebSocketEventForwarder {

        private final SimpMessagingTemplate messagingTemplate;

        public WebSocketEventForwarder(SimpMessagingTemplate messagingTemplate) {
            this.messagingTemplate = messagingTemplate;
        }

        public void handleMessage(String message, String channel) {
            // channel format: unmasked:ws:{case_id}
            // extract case_id and broadcast to STOMP topic
            String caseId = channel.replace("unmasked:ws:", "");
            messagingTemplate.convertAndSend("/topic/cases/" + caseId, message);
        }
    }
}
