"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, BookOpen, FileText, X, ExternalLink, Loader2 } from 'lucide-react';
import { StructuredContent, Citation } from '@/types';
import { cn } from '@/lib/utils';
import { getPdfUrl } from '@/lib/api';

interface StructuredResponseProps {
    content: StructuredContent;
    dict: any;
}

function CitationCard({ citation, onClose }: { citation: Citation; onClose: () => void }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleViewPdf = async () => {
        setLoading(true);
        setError(null);

        try {
            // citation.authors contains the paper_id (e.g., "02596_W1962380625")
            const response = await getPdfUrl(citation.authors);
            // Open PDF in new tab
            window.open(response.pdf_url, '_blank');
        } catch (err) {
            setError('PDF not available for this paper');
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
            onClick={onClose}
        >
            <div
                className="bg-card border border-border rounded-xl p-6 max-w-lg w-full shadow-xl"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex justify-between items-start mb-4">
                    <h3 className="text-lg font-semibold text-foreground pr-4">
                        {citation.title}
                    </h3>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-muted rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-muted-foreground" />
                    </button>
                </div>

                {citation.authors && (
                    <p className="text-sm text-muted-foreground mb-4">
                        Paper ID: {citation.authors}
                    </p>
                )}

                {citation.snippet && (
                    <div className="bg-muted/50 rounded-lg p-4 mb-4">
                        <p className="text-sm text-foreground/80 leading-relaxed">
                            {citation.snippet}
                        </p>
                    </div>
                )}

                {/* View PDF Button */}
                <button
                    onClick={handleViewPdf}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground px-4 py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Loading PDF...
                        </>
                    ) : (
                        <>
                            <ExternalLink className="w-4 h-4" />
                            View Original PDF
                        </>
                    )}
                </button>

                {error && (
                    <p className="text-sm text-red-500 mt-2 text-center">{error}</p>
                )}
            </div>
        </motion.div>
    );
}

export function StructuredResponse({ content, dict }: StructuredResponseProps) {
    const [expanded, setExpanded] = useState(false);
    const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

    return (
        <div className="space-y-6 w-full max-w-3xl">
            {/* Executive Summary Section */}
            <div className="bg-card border border-border/50 rounded-xl p-6 shadow-sm">
                <div className="flex items-center gap-2 mb-4 text-primary font-medium text-sm uppercase tracking-wider">
                    <FileText className="w-4 h-4" />
                    {dict.executiveSummary}
                </div>
                <ul className="space-y-3">
                    {content.summary.map((point, idx) => (
                        <li key={idx} className="flex gap-3 text-foreground/90 leading-relaxed">
                            <span className="block w-1.5 h-1.5 mt-2.5 rounded-full bg-primary shrink-0" />
                            <span>{point}</span>
                        </li>
                    ))}
                </ul>
            </div>

            {/* Deep Dive / Analyst View */}
            {content.details && content.details.length > 0 && (
                <div className="border border-border/50 rounded-xl overflow-hidden bg-muted/30">
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
                    >
                        <span className="font-medium text-sm flex items-center gap-2 text-muted-foreground">
                            <BookOpen className="w-4 h-4" />
                            {dict.analystView}
                        </span>
                        {expanded ? (
                            <ChevronUp className="w-4 h-4 text-muted-foreground" />
                        ) : (
                            <ChevronDown className="w-4 h-4 text-muted-foreground" />
                        )}
                    </button>

                    <AnimatePresence>
                        {expanded && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <div className="p-6 pt-0 space-y-6 border-t border-border/50">
                                    {content.details.map((section, idx) => (
                                        <div key={idx}>
                                            <h4 className="font-semibold text-foreground mb-2 text-sm">
                                                {section.title}
                                            </h4>
                                            <p className="text-muted-foreground text-sm leading-relaxed whitespace-pre-line">
                                                {section.content}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            )}

            {/* Citations */}
            {content.citations && content.citations.length > 0 && (
                <div className="pt-2">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                        {dict.keyReferences}
                    </h4>
                    <div className="grid gap-2 sm:grid-cols-2">
                        {content.citations.map((citation, index) => (
                            <button
                                key={citation.id}
                                onClick={() => setSelectedCitation(citation)}
                                className="group block p-3 rounded-lg border border-border/50 bg-card hover:border-primary/50 hover:shadow-sm transition-all text-left"
                            >
                                <div className="flex items-start gap-2">
                                    <span className="shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-semibold flex items-center justify-center">
                                        {index + 1}
                                    </span>
                                    <div className="text-sm font-medium text-foreground group-hover:text-primary line-clamp-2">
                                        {citation.title}
                                    </div>
                                </div>
                                <div className="text-xs text-muted-foreground mt-1 ml-8">
                                    Click to view excerpt
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Citation Modal */}
            <AnimatePresence>
                {selectedCitation && (
                    <CitationCard
                        citation={selectedCitation}
                        onClose={() => setSelectedCitation(null)}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}
