import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { designsApi } from '../api/designs';
import type { DesignFilters } from '../api/designs';
import type { DesignCreate, DesignUpdate, RevisionCreate } from '../types/api';

export function useDesigns(filters?: DesignFilters) {
  return useQuery({
    queryKey: ['designs', filters],
    queryFn: () => designsApi.list(filters),
  });
}

export function useDesign(id: string) {
  return useQuery({
    queryKey: ['design', id],
    queryFn: () => designsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateDesign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DesignCreate) => designsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designs'] });
    },
  });
}

export function useUpdateDesign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DesignUpdate }) =>
      designsApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['design', id] });
      queryClient.invalidateQueries({ queryKey: ['designs'] });
    },
  });
}

export function useDeleteDesign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => designsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designs'] });
    },
  });
}

export function useCreateRevision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ designId, data }: { designId: string; data: RevisionCreate }) =>
      designsApi.createRevision(designId, data),
    onSuccess: (_, { designId }) => {
      queryClient.invalidateQueries({ queryKey: ['design', designId] });
      queryClient.invalidateQueries({ queryKey: ['designs'] });
    },
  });
}

export function useDesignChat(designId: string) {
  return useQuery({
    queryKey: ['design-chat', designId],
    queryFn: () => designsApi.getChat(designId),
    enabled: !!designId,
  });
}

export function useAddChatMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ designId, message }: { designId: string; message: string }) =>
      designsApi.addChat(designId, message),
    onSuccess: (_, { designId }) => {
      queryClient.invalidateQueries({ queryKey: ['design-chat', designId] });
    },
  });
}
