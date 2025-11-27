import type express from 'express';
import { ExecutionContext } from './ExecutionContext.js';
import type { Agent } from '../agent/Agent.js';
import type { MemoryInterface } from '../memory/MemoryInterface.js';
import type { WorkflowReporter } from '../workflow/WorkflowReporter.js';
import type { DiscoveryOptions } from '../types/agent.js';

export class SkillContext<TInput = any> {
  readonly input: TInput;
  readonly executionId: string;
  readonly sessionId?: string;
  readonly workflowId?: string;
  readonly req: express.Request;
  readonly res: express.Response;
  readonly agent: Agent;
  readonly memory: MemoryInterface;
  readonly workflow: WorkflowReporter;

  constructor(params: {
    input: TInput;
    executionId: string;
    sessionId?: string;
    workflowId?: string;
    req: express.Request;
    res: express.Response;
    agent: Agent;
    memory: MemoryInterface;
    workflow: WorkflowReporter;
  }) {
    this.input = params.input;
    this.executionId = params.executionId;
    this.sessionId = params.sessionId;
    this.workflowId = params.workflowId;
    this.req = params.req;
    this.res = params.res;
    this.agent = params.agent;
    this.memory = params.memory;
    this.workflow = params.workflow;
  }

  discover(options?: DiscoveryOptions) {
    return this.agent.discover(options);
  }
}

export function getCurrentSkillContext<TInput = any>(): SkillContext<TInput> | undefined {
  const execution = ExecutionContext.getCurrent();
  if (!execution) return undefined;
  const { metadata, input, agent, req, res } = execution;
  return new SkillContext<TInput>({
    input,
    executionId: metadata.executionId,
    sessionId: metadata.sessionId,
    workflowId: metadata.workflowId,
    req,
    res,
    agent,
    memory: agent.getMemoryInterface(metadata),
    workflow: agent.getWorkflowReporter(metadata)
  });
}
