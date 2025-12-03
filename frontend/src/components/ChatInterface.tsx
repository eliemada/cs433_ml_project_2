"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Menu, User } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { InputComposer } from './InputComposer';
import { StructuredResponse } from './StructuredResponse';
import { ModelSelector } from './ModelSelector';
import { Message, StructuredContent } from '@/types';
import { cn } from '@/lib/utils';
import { chatWithRAG, ChatResponse, ChatCitation, getAvailableModels } from '@/lib/api';

/**
 * Parse LLM-generated markdown answer into structured content
 */
const parseRAGResponse = (response: ChatResponse): StructuredContent => {
    const answer = response.answer;

    // Extract Executive Summary section
    const summaryMatch = answer.match(/##?\s*Executive Summary[\s\S]*?(?=##|$)/i);
    const summaryText = summaryMatch ? summaryMatch[0] : '';

    // Parse bullet points from summary
    const summaryBullets = summaryText
        .split('\n')
        .filter(line => line.trim().startsWith('-') || line.trim().startsWith('•'))
        .map(line => line.replace(/^[\s-•*]+/, '').trim())
        .filter(line => line.length > 0);

    // If no bullets found, use the whole summary as one point
    const summary = summaryBullets.length > 0
        ? summaryBullets
        : [summaryText.replace(/##?\s*Executive Summary/i, '').trim()].filter(s => s);

    // Extract Detailed Analysis section
    const detailsMatch = answer.match(/##?\s*Detailed Analysis[\s\S]*?(?=##\s*Key References|##\s*References|$)/i);
    const detailsText = detailsMatch ? detailsMatch[0] : '';

    // Parse subsections in details
    const detailSections = detailsText
        .split(/###\s+/)
        .slice(1) // Skip the "Detailed Analysis" header
        .map(section => {
            const lines = section.split('\n');
            const title = lines[0]?.trim() || 'Analysis';
            const content = lines.slice(1).join('\n').trim();
            return { title, content };
        })
        .filter(s => s.content.length > 0);

    // If no subsections, use the whole details as one section
    const details = detailSections.length > 0
        ? detailSections
        : detailsText.replace(/##?\s*Detailed Analysis/i, '').trim()
            ? [{ title: 'Detailed Analysis', content: detailsText.replace(/##?\s*Detailed Analysis/i, '').trim() }]
            : [];

    // Transform citations
    const citations = response.citations.map((cite: ChatCitation) => ({
        id: cite.id,
        title: cite.title,
        authors: cite.authors,
        year: cite.year || '',
        snippet: cite.snippet
    }));

    return { summary, details, citations };
};

export function ChatInterface({ dict }: { dict: any }) {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const [selectedModel, setSelectedModel] = useState('openai/gpt-4o-mini');
    const scrollRef = useRef<HTMLDivElement>(null);

    // Load default model from API on mount
    useEffect(() => {
        getAvailableModels()
            .then(data => {
                if (data.default) {
                    setSelectedModel(data.default);
                }
            })
            .catch(err => {
                console.error('Failed to load default model:', err);
            });
    }, []);

    const handleNewChat = () => {
        setMessages([]);
    };

    const handleSend = async (text: string) => {
        // Add user message
        const userMsg: Message = {
            id: Date.now().toString(),
            type: 'user',
            content: text,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, userMsg]);
        setIsTyping(true);

        try {
            // Call the RAG chat API (search + LLM generation)
            const chatResponse = await chatWithRAG({
                message: text,
                top_k: 10,
                use_reranker: true,
                model: selectedModel
            });

            // Parse LLM response into structured content
            const responseContent = parseRAGResponse(chatResponse);

            const botMsg: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: responseContent,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, botMsg]);
        } catch (error) {
            console.error('Chat failed:', error);
            // Show error message
            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: {
                    summary: ['Sorry, the search service is currently unavailable. Please try again later.'],
                    details: [],
                    citations: []
                },
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsTyping(false);
        }
    };

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isTyping]);

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} onNewChat={handleNewChat} dict={dict.sidebar} />

            {/* Main Content Area */}
            <main
                className={cn(
                    "flex-1 flex flex-col h-full transition-all duration-300 ease-in-out relative",
                    sidebarOpen ? "ml-64" : "ml-0"
                )}
            >
                {/* Header */}
                <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-background/80 backdrop-blur-sm sticky top-0 z-10">
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-2 hover:bg-muted rounded-lg transition-colors"
                    >
                        <Menu className="w-5 h-5 text-muted-foreground" />
                    </button>
                    <div className="flex items-center gap-4">
                        {/* Model Selector */}
                        <ModelSelector
                            selectedModel={selectedModel}
                            onModelChange={setSelectedModel}
                        />
                        {/* Placeholder for User Profile */}
                        <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                            <User className="w-4 h-4 text-muted-foreground" />
                        </div>
                    </div>
                </header>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
                    <div className="max-w-3xl mx-auto space-y-8 pb-4">
                        {messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-4">
                                <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4">
                                    <div className="w-8 h-8 bg-primary rounded-full animate-pulse" />
                                </div>
                                <h1 className="text-2xl font-semibold tracking-tight">
                                    {dict.chat.headerTitle}
                                </h1>
                                <p className="text-muted-foreground max-w-md">
                                    {dict.chat.emptyDescription}
                                </p>
                            </div>
                        )}

                        {messages.map((msg) => (
                            <div
                                key={msg.id}
                                className={cn(
                                    "flex gap-4",
                                    msg.type === 'user' ? "flex-row-reverse" : "flex-row"
                                )}
                            >
                                {/* Avatar */}
                                <div className={cn(
                                    "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-1",
                                    msg.type === 'user' ? "bg-primary text-primary-foreground" : "bg-secondary"
                                )}>
                                    {msg.type === 'user' ? <User className="w-4 h-4" /> : <div className="w-4 h-4 bg-primary rounded-full" />}
                                </div>

                                {/* Content */}
                                <div className={cn(
                                    "flex-1 max-w-[85%]",
                                    msg.type === 'user' ? "text-right" : "text-left"
                                )}>
                                    {msg.type === 'user' ? (
                                        <div className="bg-primary text-primary-foreground px-4 py-2.5 rounded-2xl rounded-tr-sm inline-block text-sm">
                                            {msg.content as string}
                                        </div>
                                    ) : (
                                        <StructuredResponse content={msg.content as StructuredContent} dict={dict.response} />
                                    )}
                                </div>
                            </div>
                        ))}

                        {isTyping && (
                            <div className="flex gap-4">
                                <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                                    <div className="w-4 h-4 bg-primary rounded-full" />
                                </div>
                                <div className="flex items-center gap-1 h-8">
                                    <span className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                    <span className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                    <span className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce" />
                                </div>
                            </div>
                        )}
                        <div ref={scrollRef} />
                    </div>
                </div>

                {/* Input Area */}
                <div className="p-6 bg-background/80 backdrop-blur-sm border-t border-border/50">
                    <InputComposer onSend={handleSend} isTyping={isTyping} dict={dict.input} />
                </div>
            </main>
        </div>
    );
}
