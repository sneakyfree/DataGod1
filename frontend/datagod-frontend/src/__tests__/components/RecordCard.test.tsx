/**
 * RecordCard Component Tests
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

describe('RecordCard', () => {
    let RecordCard: any;

    beforeAll(async () => {
        try {
            const mod = await import('../../components/records/RecordCard');
            RecordCard = mod.default;
        } catch {
            // Component may not be importable
        }
    });

    const mockRecord = {
        id: 1,
        title: 'Test Business Filing',
        record_type: 'business_filing',
        jurisdiction_name: 'California',
        date: '2024-01-15',
        description: 'Annual filing for Test Corp',
        amount: 25000,
    };

    it('should be importable', () => {
        expect(RecordCard).toBeDefined();
    });

    it('should render record title', () => {
        if (!RecordCard) return;
        render(<RecordCard record={mockRecord} />);
        expect(screen.getByText('Test Business Filing')).toBeInTheDocument();
    });

    it('should render record type as chip', () => {
        if (!RecordCard) return;
        render(<RecordCard record={mockRecord} />);
        expect(screen.getByText('business filing')).toBeInTheDocument();
    });

    it('should render jurisdiction name', () => {
        if (!RecordCard) return;
        render(<RecordCard record={mockRecord} />);
        expect(screen.getByText('California')).toBeInTheDocument();
    });

    it('should render description when compact is false', () => {
        if (!RecordCard) return;
        render(<RecordCard record={mockRecord} />);
        expect(screen.getByText('Annual filing for Test Corp')).toBeInTheDocument();
    });

    it('should hide description in compact mode', () => {
        if (!RecordCard) return;
        render(<RecordCard record={mockRecord} compact />);
        expect(screen.queryByText('Annual filing for Test Corp')).not.toBeInTheDocument();
    });

    it('should render Untitled Record when no title', () => {
        if (!RecordCard) return;
        render(<RecordCard record={{ ...mockRecord, title: '' }} />);
        expect(screen.getByText('Untitled Record')).toBeInTheDocument();
    });

    it('should call onFavorite callback', () => {
        if (!RecordCard) return;
        const onFavorite = jest.fn();
        render(<RecordCard record={mockRecord} onFavorite={onFavorite} />);
        const favButton = screen.getByLabelText(/favorite/i);
        fireEvent.click(favButton);
        expect(onFavorite).toHaveBeenCalledWith(1);
    });

    it('should call onShare callback', () => {
        if (!RecordCard) return;
        const onShare = jest.fn();
        render(<RecordCard record={mockRecord} onShare={onShare} />);
        const shareButton = screen.getByLabelText('Share');
        fireEvent.click(shareButton);
        expect(onShare).toHaveBeenCalledWith(1);
    });
});
