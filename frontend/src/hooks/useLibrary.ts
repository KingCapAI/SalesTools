import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { libraryApi } from '../api/library';
import type { Industry } from '../types/api';

export function useLibraryDesigns(industry?: string) {
  return useQuery({
    queryKey: ['library-designs', industry || 'all'],
    queryFn: () => libraryApi.list(industry),
  });
}

export function useLibraryIndustries() {
  return useQuery({
    queryKey: ['library-industries'],
    queryFn: () => libraryApi.industries(),
  });
}

export function usePublishToLibrary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ designId, industries }: { designId: string; industries: Industry[] }) =>
      libraryApi.publish(designId, industries),
    onSuccess: (_, { designId }) => {
      queryClient.invalidateQueries({ queryKey: ['library-designs'] });
      queryClient.invalidateQueries({ queryKey: ['library-industries'] });
      queryClient.invalidateQueries({ queryKey: ['design', designId] });
      queryClient.invalidateQueries({ queryKey: ['custom-design', designId] });
    },
  });
}

export function useUnpublishFromLibrary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (designId: string) => libraryApi.unpublish(designId),
    onSuccess: (_, designId) => {
      queryClient.invalidateQueries({ queryKey: ['library-designs'] });
      queryClient.invalidateQueries({ queryKey: ['library-industries'] });
      queryClient.invalidateQueries({ queryKey: ['design', designId] });
      queryClient.invalidateQueries({ queryKey: ['custom-design', designId] });
    },
  });
}

export function useRemixData(designId: string | null) {
  return useQuery({
    queryKey: ['library-remix-data', designId],
    queryFn: () => libraryApi.remixData(designId!),
    enabled: !!designId,
  });
}
