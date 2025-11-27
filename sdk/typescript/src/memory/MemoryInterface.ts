import type { MemoryScope } from '../types/agent.js';
import type { MemoryClient, MemoryRequestMetadata, VectorSearchOptions } from './MemoryClient.js';
import type { MemoryEventClient } from './MemoryEventClient.js';

export interface MemoryChangeEvent {
  key: string;
  data: any;
  scope: MemoryScope;
  scopeId: string;
  timestamp: string | Date;
  agentId: string;
}

export type MemoryWatchHandler = (event: MemoryChangeEvent) => Promise<void> | void;

export class MemoryInterface {
  private readonly client: MemoryClient;
  private readonly eventClient?: MemoryEventClient;
  private readonly defaultScope: MemoryScope;
  private readonly defaultScopeId?: string;
  private readonly metadata?: MemoryRequestMetadata;

  constructor(params: {
    client: MemoryClient;
    eventClient?: MemoryEventClient;
    defaultScope?: MemoryScope;
    defaultScopeId?: string;
    metadata?: MemoryRequestMetadata;
  }) {
    this.client = params.client;
    this.eventClient = params.eventClient;
    this.defaultScope = params.defaultScope ?? 'workflow';
    this.defaultScopeId = params.defaultScopeId;
    this.metadata = params.metadata;
  }

  async set(key: string, data: any, scope: MemoryScope = this.defaultScope, scopeId = this.defaultScopeId) {
    await this.client.set(key, data, {
      scope,
      scopeId,
      metadata: this.metadata
    });
  }

  get<T = any>(key: string, scope: MemoryScope = this.defaultScope, scopeId = this.defaultScopeId) {
    return this.client.get<T>(key, {
      scope,
      scopeId,
      metadata: this.metadata
    });
  }

  async setVector(
    key: string,
    embedding: number[],
    metadata?: any,
    scope: MemoryScope = this.defaultScope,
    scopeId = this.defaultScopeId
  ) {
    await this.client.setVector(key, embedding, metadata, {
      scope,
      scopeId,
      metadata: this.metadata
    });
  }

  async deleteVector(key: string, scope: MemoryScope = this.defaultScope, scopeId = this.defaultScopeId) {
    await this.client.deleteVector(key, {
      scope,
      scopeId,
      metadata: this.metadata
    });
  }

  searchVector(queryEmbedding: number[], options: Omit<VectorSearchOptions, 'metadata'> = {}) {
    return this.client.searchVector(queryEmbedding, {
      ...options,
      metadata: this.metadata
    });
  }

  onEvent(handler: MemoryWatchHandler) {
    this.eventClient?.onEvent(handler);
  }
}
