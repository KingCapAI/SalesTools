import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customDesignsApi } from '../api/customDesigns';
import type { CustomDesignFilters } from '../api/customDesigns';
import type { CustomDesignCreate, CustomDesignUpdate, RevisionCreate, DecorationLocation } from '../types/api';

export function useCustomDesigns(filters?: CustomDesignFilters) {
  return useQuery({
    queryKey: ['custom-designs', filters],
    queryFn: () => customDesignsApi.list(filters),
  });
}

export function useCustomDesign(id: string) {
  return useQuery({
    queryKey: ['custom-design', id],
    queryFn: () => customDesignsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateCustomDesign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CustomDesignCreate) => customDesignsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-designs'] });
    },
  });
}

export function useUpdateCustomDesign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CustomDesignUpdate }) =>
      customDesignsApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['custom-design', id] });
      queryClient.invalidateQueries({ queryKey: ['custom-designs'] });
    },
  });
}

export function useDeleteCustomDesign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => customDesignsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-designs'] });
    },
  });
}

export function useRegenerateCustomDesign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => customDesignsApi.regenerate(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['custom-design', id] });
      queryClient.invalidateQueries({ queryKey: ['custom-designs'] });
    },
  });
}

export function useCreateCustomDesignRevision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ designId, data }: { designId: string; data: RevisionCreate }) =>
      customDesignsApi.createRevision(designId, data),
    onSuccess: (_, { designId }) => {
      queryClient.invalidateQueries({ queryKey: ['custom-design', designId] });
      queryClient.invalidateQueries({ queryKey: ['custom-designs'] });
    },
  });
}

export function useCustomDesignChat(designId: string) {
  return useQuery({
    queryKey: ['custom-design-chat', designId],
    queryFn: () => customDesignsApi.getChat(designId),
    enabled: !!designId,
  });
}

export function useAddCustomDesignChatMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ designId, message }: { designId: string; message: string }) =>
      customDesignsApi.addChat(designId, message),
    onSuccess: (_, { designId }) => {
      queryClient.invalidateQueries({ queryKey: ['custom-design-chat', designId] });
    },
  });
}

export function useUploadLocationLogo() {
  return useMutation({
    mutationFn: ({ file, location }: { file: File; location: DecorationLocation }) =>
      customDesignsApi.uploadLocationLogo(file, location),
  });
}

export function useUploadReferenceHat() {
  return useMutation({
    mutationFn: (file: File) => customDesignsApi.uploadReferenceHat(file),
  });
}
