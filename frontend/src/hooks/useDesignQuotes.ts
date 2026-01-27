import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { designQuotesApi } from '../api/designQuotes';
import type { DesignQuoteCreate, DesignQuoteUpdate } from '../api/designQuotes';

export function useDesignQuote(designId: string) {
  return useQuery({
    queryKey: ['design-quote', designId],
    queryFn: () => designQuotesApi.get(designId),
    enabled: !!designId,
  });
}

export function useCreateDesignQuote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ designId, data }: { designId: string; data: DesignQuoteCreate }) =>
      designQuotesApi.create(designId, data),
    onSuccess: (_, { designId }) => {
      queryClient.invalidateQueries({ queryKey: ['design-quote', designId] });
      queryClient.invalidateQueries({ queryKey: ['design', designId] });
      queryClient.invalidateQueries({ queryKey: ['designs'] });
    },
  });
}

export function useUpdateDesignQuote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ designId, data }: { designId: string; data: DesignQuoteUpdate }) =>
      designQuotesApi.update(designId, data),
    onSuccess: (_, { designId }) => {
      queryClient.invalidateQueries({ queryKey: ['design-quote', designId] });
      queryClient.invalidateQueries({ queryKey: ['design', designId] });
      queryClient.invalidateQueries({ queryKey: ['designs'] });
    },
  });
}

export function useDeleteDesignQuote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (designId: string) => designQuotesApi.delete(designId),
    onSuccess: (_, designId) => {
      queryClient.invalidateQueries({ queryKey: ['design-quote', designId] });
      queryClient.invalidateQueries({ queryKey: ['design', designId] });
      queryClient.invalidateQueries({ queryKey: ['designs'] });
    },
  });
}

export function useExportDesignWithQuote() {
  return useMutation({
    mutationFn: ({ designId, format }: { designId: string; format: 'xlsx' | 'pdf' }) =>
      designQuotesApi.exportWithDesign(designId, format),
    onSuccess: (blob, { designId, format }) => {
      // Download the file
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `design_${designId}_quote.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}
