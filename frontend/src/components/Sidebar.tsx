"use client";

import React from 'react';
import { Plus, BookOpen, Database, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
    isOpen: boolean;
    onToggle: () => void;
    onNewChat: () => void;
    dict: any;
}

export function Sidebar({ isOpen, onNewChat, dict }: SidebarProps) {
    return (
        <div
            className={cn(
                "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border transform transition-transform duration-300 ease-in-out flex flex-col",
                isOpen ? "translate-x-0" : "-translate-x-full"
            )}
        >
            {/* Header */}
            <div className="p-4 border-b border-border flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <div className="w-4 h-4 rounded-full bg-primary" />
                </div>
                <span className="font-semibold text-foreground tracking-tight">{dict.appName}</span>
            </div>

            {/* New Chat Button */}
            <div className="p-3">
                <button
                    onClick={onNewChat}
                    className="w-full flex items-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-xl hover:opacity-90 transition-opacity shadow-sm"
                >
                    <Plus className="w-4 h-4" />
                    <span className="text-sm font-medium">{dict.newChat}</span>
                </button>
            </div>

            {/* Info Section */}
            <div className="flex-1 overflow-y-auto py-4 px-3">
                <div className="space-y-4">
                    <div className="p-4 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                            <Database className="w-4 h-4 text-primary" />
                            Knowledge Base
                        </div>
                        <p className="text-xs text-muted-foreground">
                            ~1,000 academic papers on intellectual property, innovation, and economic policy
                        </p>
                    </div>

                    <div className="p-4 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                            <Sparkles className="w-4 h-4 text-primary" />
                            Powered by
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Semantic search + ZeroEntropy reranking + GPT-4o-mini
                        </p>
                    </div>

                    <div className="p-4 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                            <BookOpen className="w-4 h-4 text-primary" />
                            How to use
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Ask policy questions in natural language. Click citations to view source excerpts and original PDFs.
                        </p>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border">
                <p className="text-xs text-muted-foreground text-center">
                    POC - CS433 RAG Project
                </p>
            </div>
        </div>
    );
}
