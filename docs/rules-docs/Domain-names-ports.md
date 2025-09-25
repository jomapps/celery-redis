# Auto-Movie App: Prompt Management & Testing System

## Overview
The Auto-Movie app serves as the central dashboard where users interact with the AI movie production platform. This feature adds comprehensive prompt management capabilities with real-time testing, allowing creative teams to iterate on AI agent prompts and see immediate results without running full production pipelines.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Auto-Movie App                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│  │  Dashboard UI   │ │ Prompt Manager  │ │ Test Studio │││
│  │  • Projects     │ │ • CRUD Prompts  │ │ • Live Test │││
│  │  • Progress     │ │ • Versioning    │ │ • Results   │││
│  │  • Analytics    │ │ • Approval      │ │ • Compare   │││
│  └─────────────────┘ └─────────────────┘ └─────────────┘││
│                              │                          ││
│  ┌─────────────────────────────────────────────────────┐││
│  │              PayloadCMS Collections                 │││
│  │  • Projects    • Prompts     • Test Results         │││
│  │  • Sessions    • Versions    • Agent Configs        │││
│  └─────────────────────────────────────────────────────┘││
│                              │                          ││
│  ┌─────────────────────────────────────────────────────┐││
│  │                API Layer                            │││
│  │  • Prompt CRUD   • Testing API   • Agent Proxy     │││
│  └─────────────────────────────────────────────────────┘││
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│              Background Services                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│  │ Celery Tasks    │ │ MCP Brain       │ │ Agents      ││
│  │ • Test Requests │ │ • Knowledge     │ │ • 50+ Types ││
│  │ • Media Gen     │ │ • Embeddings    │ │ • BAML      ││
│  └─────────────────┘ └─────────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────┘
```

## PayloadCMS Collections

### 1. Enhanced Prompts Collection

```typescript
// src/collections/Prompts.ts
const Prompts: CollectionConfig = {
  slug: 'prompts',
  admin: {
    useAsTitle: 'display_name',
    defaultColumns: ['display_name', 'agent_type', 'version', 'status', 'updatedAt'],
    group: 'Agent Management',
  },
  access: {
    read: ({ req: { user } }) => {
      if (user?.role === 'admin') return true
      return { created_by: { equals: user?.id } }
    },
    create: ({ req: { user } }) => user?.role !== 'viewer',
    update: ({ req: { user } }) => {
      if (user?.role === 'admin') return true
      return { created_by: { equals: user?.id } }
    },
  },
  fields: [
    {
      name: 'display_name',
      type: 'text',
      required: true,
      admin: {
        placeholder: 'e.g., Character Creator - Protagonist Template'
      }
    },
    {
      name: 'agent_type',
      type: 'select',
      required: true,
      index: true,
      options: [
        { label: 'Series Creator', value: 'series_creator' },
        { label: 'Story Architect', value: 'story_architect' },
        { label: 'Character Creator', value: 'character_creator' },
        { label: 'Character Designer', value: 'character_designer' },
        { label: 'Voice Creator', value: 'voice_creator' },
        { label: 'Concept Artist', value: 'concept_artist' },
        { label: 'Environment Designer', value: 'environment_designer' },
        { label: 'Scene Director', value: 'scene_director' },
        { label: 'Storyboard Artist', value: 'storyboard_artist' },
        { label: 'Image Generation', value: 'image_generation' },
        { label: 'Video Generation', value: 'video_generation' },
        { label: 'Audio Composer', value: 'audio_composer' },
        { label: 'Dialogue Writer', value: 'dialogue_writer' },
        // ... all 50+ agent types
      ],
    },
    {
      name: 'template_key',
      type: 'text',
      required: true,
      unique: true,
      admin: {
        description: 'Unique identifier for this prompt template',
        placeholder: 'character_creator_protagonist_v1'
      }
    },
    {
      name: 'baml_template',
      type: 'code',
      required: true,
      admin: {
        language: 'handlebars',
        description: 'BAML template with proper syntax and variables'
      }
    },
    {
      name: 'input_schema',
      type: 'json',
      required: true,
      admin: {
        description: 'JSON schema defining required input parameters for this prompt'
      }
    },
    {
      name: 'output_schema',
      type: 'json',
      required: true,
      admin: {
        description: 'Expected BAML output structure for validation'
      }
    },
    {
      name: 'test_parameters',
      type: 'json',
      admin: {
        description: 'Default test parameters for quick testing'
      }
    },
    {
      name: 'version',
      type: 'text',
      defaultValue: '1.0.0',
      admin: {
        description: 'Semantic version (major.minor.patch)'
      }
    },
    {
      name: 'status',
      type: 'select',
      defaultValue: 'draft',
      options: [
        { label: 'Draft', value: 'draft' },
        { label: 'Testing', value: 'testing' },
        { label: 'Active', value: 'active' },
        { label: 'Deprecated', value: 'deprecated' },
        { label: 'Archived', value: 'archived' },
      ],
    },
    {
      name: 'scope',
      type: 'group',
      fields: [
        {
          name: 'project_specific',
          type: 'relationship',
          relationTo: 'projects',
          hasMany: true,
          admin: {
            description: 'Leave empty for global prompts'
          }
        },
        {
          name: 'genre_filters',
          type: 'select',
          hasMany: true,
          options: [
            { label: 'Action', value: 'action' },
            { label: 'Comedy', value: 'comedy' },
            { label: 'Drama', value: 'drama' },
            { label: 'Horror', value: 'horror' },
            { label: 'Sci-Fi', value: 'sci-fi' },
            { label: 'Thriller', value: 'thriller' },
            { label: 'Romance', value: 'romance' },
            { label: 'Documentary', value: 'documentary' },
          ],
        },
        {
          name: 'target_audience',
          type: 'select',
          hasMany: true,
          options: [
            { label: 'Children', value: 'children' },
            { label: 'Family', value: 'family' },
            { label: 'Teen', value: 'teen' },
            { label: 'Adult', value: 'adult' },
          ],
        }
      ]
    },
    {
      name: 'metadata',
      type: 'group',
      fields: [
        {
          name: 'created_by',
          type: 'relationship',
          relationTo: 'users',
          required: true,
          admin: {
            position: 'sidebar'
          }
        },
        {
          name: 'approved_by',
          type: 'relationship',
          relationTo: 'users',
          admin: {
            description: 'Creative lead or admin approval',
            position: 'sidebar'
          }
        },
        {
          name: 'approval_notes',
          type: 'textarea',
          admin: {
            condition: (data) => !!data.metadata?.approved_by
          }
        },
        {
          name: 'tags',
          type: 'select',
          hasMany: true,
          options: [
            { label: 'High Priority', value: 'high_priority' },
            { label: 'Experimental', value: 'experimental' },
            { label: 'Performance Critical', value: 'performance_critical' },
            { label: 'Client Specific', value: 'client_specific' },
            { label: 'Template', value: 'template' },
          ]
        }
      ]
    },
    {
      name: 'performance',
      type: 'group',
      admin: {
        description: 'Performance metrics and testing results'
      },
      fields: [
        {
          name: 'last_tested',
          type: 'date',
          admin: {
            date: {
              pickerAppearance: 'dayAndTime'
            }
          }
        },
        {
          name: 'test_count',
          type: 'number',
          defaultValue: 0,
          admin: {
            description: 'Total number of tests run'
          }
        },
        {
          name: 'success_rate',
          type: 'number',
          min: 0,
          max: 100,
          admin: {
            description: 'Success rate percentage'
          }
        },
        {
          name: 'avg_processing_time',
          type: 'number',
          admin: {
            description: 'Average processing time in seconds'
          }
        },
        {
          name: 'performance_notes',
          type: 'textarea',
        }
      ]
    }
  ],
  hooks: {
    beforeChange: [
      ({ operation, data, req }) => {
        if (operation === 'create') {
          data.metadata = { 
            ...data.metadata,
            created_by: req.user.id 
          }
        }
        
        // Auto-increment version for updates
        if (operation === 'update' && data.baml_template !== req.originalDoc.baml_template) {
          const [major, minor, patch] = (data.version || '1.0.0').split('.').map(Number)
          data.version = `${major}.${minor}.${patch + 1}`
        }
        
        return data
      }
    ]
  },
  timestamps: true,
}
```

### 2. Test Results Collection

```typescript
// src/collections/TestResults.ts
const TestResults: CollectionConfig = {
  slug: 'test-results',
  admin: {
    useAsTitle: 'test_name',
    defaultColumns: ['test_name', 'prompt', 'status', 'createdAt'],
    group: 'Testing',
  },
  fields: [
    {
      name: 'test_name',
      type: 'text',
      required: true,
    },
    {
      name: 'prompt',
      type: 'relationship',
      relationTo: 'prompts',
      required: true,
    },
    {
      name: 'test_parameters',
      type: 'json',
      required: true,
      admin: {
        description: 'Input parameters used for this test'
      }
    },
    {
      name: 'status',
      type: 'select',
      defaultValue: 'running',
      options: [
        { label: 'Running', value: 'running' },
        { label: 'Completed', value: 'completed' },
        { label: 'Failed', value: 'failed' },
        { label: 'Cancelled', value: 'cancelled' },
      ]
    },
    {
      name: 'result',
      type: 'group',
      fields: [
        {
          name: 'output_data',
          type: 'json',
          admin: {
            description: 'Raw output from the agent'
          }
        },
        {
          name: 'generated_media',
          type: 'relationship',
          relationTo: 'media',
          hasMany: true,
          admin: {
            description: 'Media files generated during test'
          }
        },
        {
          name: 'processing_time',
          type: 'number',
          admin: {
            description: 'Time taken to process in seconds'
          }
        },
        {
          name: 'tokens_used',
          type: 'number',
          admin: {
            description: 'Number of tokens consumed'
          }
        }
      ]
    },
    {
      name: 'error_details',
      type: 'group',
      admin: {
        condition: (data) => data.status === 'failed'
      },
      fields: [
        {
          name: 'error_message',
          type: 'text',
        },
        {
          name: 'stack_trace',
          type: 'code',
          admin: {
            language: 'text'
          }
        },
        {
          name: 'retry_count',
          type: 'number',
          defaultValue: 0,
        }
      ]
    },
    {
      name: 'test_context',
      type: 'group',
      fields: [
        {
          name: 'triggered_by',
          type: 'relationship',
          relationTo: 'users',
          required: true,
        },
        {
          name: 'test_type',
          type: 'select',
          options: [
            { label: 'Manual Test', value: 'manual' },
            { label: 'Automated Test', value: 'automated' },
            { label: 'A/B Comparison', value: 'ab_test' },
            { label: 'Performance Test', value: 'performance' },
          ]
        },
        {
          name: 'comparison_baseline',
          type: 'relationship',
          relationTo: 'test-results',
          admin: {
            description: 'Reference test result for comparison'
          }
        }
      ]
    }
  ],
  timestamps: true,
}
```

### 3. Agent Configurations Collection

```typescript
// src/collections/AgentConfigs.ts
const AgentConfigs: CollectionConfig = {
  slug: 'agent-configs',
  admin: {
    useAsTitle: 'agent_type',
    group: 'Agent Management',
  },
  fields: [
    {
      name: 'agent_type',
      type: 'text',
      required: true,
      unique: true,
    },
    {
      name: 'display_name',
      type: 'text',
      required: true,
    },
    {
      name: 'description',
      type: 'textarea',
    },
    {
      name: 'input_parameters',
      type: 'json',
      required: true,
      admin: {
        description: 'JSON schema for agent input parameters'
      }
    },
    {
      name: 'output_types',
      type: 'select',
      hasMany: true,
      options: [
        { label: 'Text', value: 'text' },
        { label: 'JSON', value: 'json' },
        { label: 'Image', value: 'image' },
        { label: 'Video', value: 'video' },
        { label: 'Audio', value: 'audio' },
        { label: 'Document', value: 'document' },
      ]
    },
    {
      name: 'testing_enabled',
      type: 'checkbox',
      defaultValue: true,
      admin: {
        description: 'Whether this agent supports real-time testing'
      }
    },
    {
      name: 'default_test_params',
      type: 'json',
      admin: {
        condition: (data) => data.testing_enabled,
        description: 'Default parameters for testing this agent'
      }
    },
    {
      name: 'processing_time_estimate',
      type: 'number',
      admin: {
        description: 'Estimated processing time in seconds'
      }
    },
    {
      name: 'resource_requirements',
      type: 'group',
      fields: [
        {
          name: 'gpu_required',
          type: 'checkbox',
          defaultValue: false,
        },
        {
          name: 'memory_requirement',
          type: 'select',
          options: [
            { label: 'Low (< 1GB)', value: 'low' },
            { label: 'Medium (1-4GB)', value: 'medium' },
            { label: 'High (4-8GB)', value: 'high' },
            { label: 'Very High (> 8GB)', value: 'very_high' },
          ]
        },
        {
          name: 'concurrent_limit',
          type: 'number',
          defaultValue: 5,
          admin: {
            description: 'Maximum concurrent executions'
          }
        }
      ]
    }
  ],
  timestamps: true,
}
```

## API Endpoints

### 1. Prompt Management APIs

```typescript
// pages/api/prompts/index.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  switch (req.method) {
    case 'GET':
      return await getPrompts(req, res)
    case 'POST':
      return await createPrompt(req, res)
    default:
      return res.status(405).json({ error: 'Method not allowed' })
  }
}

async function getPrompts(req: NextApiRequest, res: NextApiResponse) {
  const { 
    agent_type, 
    status, 
    page = 1, 
    limit = 20,
    search,
    genre,
    project_id 
  } = req.query

  try {
    const payload = await getPayloadClient()
    
    // Build query filters
    const where: any = { and: [] }
    
    if (agent_type) where.and.push({ agent_type: { equals: agent_type } })
    if (status) where.and.push({ status: { equals: status } })
    if (search) {
      where.and.push({
        or: [
          { display_name: { contains: search } },
          { template_key: { contains: search } },
          { baml_template: { contains: search } }
        ]
      })
    }
    if (genre) {
      where.and.push({
        or: [
          { 'scope.genre_filters': { contains: genre } },
          { 'scope.genre_filters': { exists: false } }
        ]
      })
    }
    if (project_id) {
      where.and.push({
        or: [
          { 'scope.project_specific': { contains: project_id } },
          { 'scope.project_specific': { exists: false } }
        ]
      })
    }

    const result = await payload.find({
      collection: 'prompts',
      where: where.and.length > 0 ? where : undefined,
      page: parseInt(page as string),
      limit: parseInt(limit as string),
      sort: '-updatedAt'
    })

    res.status(200).json(result)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
}

async function createPrompt(req: NextApiRequest, res: NextApiResponse) {
  try {
    const payload = await getPayloadClient()
    
    const result = await payload.create({
      collection: 'prompts',
      data: {
        ...req.body,
        metadata: {
          ...req.body.metadata,
          created_by: req.user?.id
        }
      }
    })

    res.status(201).json(result)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
}
```

```typescript
// pages/api/prompts/[id]/index.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query

  switch (req.method) {
    case 'GET':
      return await getPrompt(req, res, id as string)
    case 'PUT':
      return await updatePrompt(req, res, id as string)
    case 'DELETE':
      return await deletePrompt(req, res, id as string)
    default:
      return res.status(405).json({ error: 'Method not allowed' })
  }
}
```

```typescript
// pages/api/prompts/[id]/duplicate.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { id } = req.query
  const { new_version, new_name } = req.body

  try {
    const payload = await getPayloadClient()
    
    // Get original prompt
    const original = await payload.findByID({
      collection: 'prompts',
      id: id as string
    })

    if (!original) {
      return res.status(404).json({ error: 'Prompt not found' })
    }

    // Create duplicate with modifications
    const duplicate = await payload.create({
      collection: 'prompts',
      data: {
        ...original,
        id: undefined, // Remove ID to create new document
        display_name: new_name || `${original.display_name} (Copy)`,
        template_key: `${original.template_key}_copy_${Date.now()}`,
        version: new_version || '1.0.0',
        status: 'draft',
        metadata: {
          ...original.metadata,
          created_by: req.user?.id,
          approved_by: undefined,
          approval_notes: undefined
        }
      }
    })

    res.status(201).json(duplicate)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
}
```

### 2. Testing APIs

```typescript
// pages/api/prompts/[id]/test.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { id } = req.query
  const { test_parameters, test_name, comparison_baseline } = req.body

  try {
    const payload = await getPayloadClient()
    
    // Get prompt details
    const prompt = await payload.findByID({
      collection: 'prompts',
      id: id as string
    })

    if (!prompt) {
      return res.status(404).json({ error: 'Prompt not found' })
    }

    // Create test result record
    const testResult = await payload.create({
      collection: 'test-results',
      data: {
        test_name: test_name || `Test ${Date.now()}`,
        prompt: prompt.id,
        test_parameters,
        status: 'running',
        test_context: {
          triggered_by: req.user?.id,
          test_type: 'manual',
          comparison_baseline
        }
      }
    })

    // Submit test to Celery task queue
    const taskService = new CeleryTaskService()
    const task = await taskService.submitTask({
      projectId: 'test_project', // Special test project
      taskType: 'test_prompt',
      taskData: {
        prompt_id: prompt.id,
        prompt_template: prompt.baml_template,
        agent_type: prompt.agent_type,
        test_parameters,
        test_result_id: testResult.id
      },
      metadata: {
        userId: req.user?.id,
        testResultId: testResult.id
      }
    })

    // Update test result with task ID
    await payload.update({
      collection: 'test-results',
      id: testResult.id,
      data: {
        ...testResult,
        task_id: task.task_id
      }
    })

    res.status(201).json({
      test_result: testResult,
      task_id: task.task_id,
      message: 'Test submitted successfully'
    })

  } catch (error) {
    console.error('Test submission error:', error)
    res.status(500).json({ error: error.message })
  }
}
```

```typescript
// pages/api/test-results/[id]/index.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query

  if (req.method === 'GET') {
    try {
      const payload = await getPayloadClient()
      
      const testResult = await payload.findByID({
        collection: 'test-results',
        id: id as string,
        depth: 2 // Include related prompt and media
      })

      if (!testResult) {
        return res.status(404).json({ error: 'Test result not found' })
      }

      // If test is still running, check task status
      if (testResult.status === 'running' && testResult.task_id) {
        const taskService = new CeleryTaskService()
        const taskStatus = await taskService.getTaskStatus(testResult.task_id)
        
        // Update status if task completed
        if (taskStatus.status !== 'running') {
          const updatedResult = await payload.update({
            collection: 'test-results',
            id: testResult.id,
            data: {
              status: taskStatus.status,
              result: taskStatus.result,
              error_details: taskStatus.error ? {
                error_message: taskStatus.error,
                retry_count: testResult.error_details?.retry_count || 0
              } : undefined
            }
          })
          
          return res.status(200).json(updatedResult)
        }
      }

      res.status(200).json(testResult)
    } catch (error) {
      res.status(500).json({ error: error.message })
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' })
  }
}
```

### 3. Agent Configuration APIs

```typescript
// pages/api/agents/configs.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    try {
      const payload = await getPayloadClient()
      
      const configs = await payload.find({
        collection: 'agent-configs',
        sort: 'display_name',
        limit: 100
      })

      res.status(200).json(configs)
    } catch (error) {
      res.status(500).json({ error: error.message })
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' })
  }
}
```

```typescript
// pages/api/agents/[agent_type]/test-form.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { agent_type } = req.query

  if (req.method === 'GET') {
    try {
      const payload = await getPayloadClient()
      
      // Get agent configuration
      const config = await payload.find({
        collection: 'agent-configs',
        where: {
          agent_type: { equals: agent_type }
        },
        limit: 1
      })

      if (!config.docs.length) {
        return res.status(404).json({ error: 'Agent configuration not found' })
      }

      const agentConfig = config.docs[0]

      // Generate dynamic form schema based on input parameters
      const formSchema = generateFormSchema(agentConfig.input_parameters)

      res.status(200).json({
        agent_config: agentConfig,
        form_schema: formSchema,
        default_values: agentConfig.default_test_params || {}
      })

    } catch (error) {
      res.status(500).json({ error: error.message })
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' })
  }
}

function generateFormSchema(inputParameters: any): any {
  // Convert JSON schema to React Hook Form compatible schema
  const schema = {
    type: 'object',
    properties: {},
    required: []
  }

  for (const [key, param] of Object.entries(inputParameters.properties || {})) {
    schema.properties[key] = {
      ...param,
      label: param.title || key,
      placeholder: param.description || `Enter ${key}`,
    }

    if (inputParameters.required?.includes(key)) {
      schema.required.push(key)
    }
  }

  return schema
}
```

## UI Components

### 1. Prompt Management Dashboard

```typescript
// pages/prompts/index.tsx
import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Layout from '../../components/Layout'
import PromptCard from '../../components/prompts/PromptCard'
import PromptFilters from '../../components/prompts/PromptFilters'
import { Button } from '../../components/ui/Button'

export default function PromptsPage() {
  const router = useRouter()
  const [prompts, setPrompts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    agent_type: '',
    status: '',
    search: '',
    genre: '',
    page: 1,
    limit: 12
  })

  useEffect(() => {
    fetchPrompts()
  }, [filters])

  const fetchPrompts = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams(
        Object.entries(filters).filter(([_, value]) => value)
      )
      
      const response = await fetch(`/api/prompts?${params}`)
      const data = await response.json()
      
      setPrompts(data.docs || [])
    } catch (error) {
      console.error('Error fetching prompts:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Prompt Management">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Prompt Management</h1>
            <p className="text-gray-600 mt-2">
              Create, edit, and test AI agent prompts
            </p>
          </div>
          <Button 
            onClick={() => router.push('/prompts/create')}
            className="bg-blue-600 hover:bg-blue-700"
          >
            + Create Prompt
          </Button>
        </div>

        {/* Filters */}
        <PromptFilters 
          filters={filters} 
          onChange={setFilters}
          onReset={() => setFilters({ 
            agent_type: '', status: '', search: '', genre: '', page: 1, limit: 12 
          })}
        />

        {/* Prompts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow-sm p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded mb-4"></div>
                <div className="h-3 bg-gray-200 rounded mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            ))
          ) : prompts.length > 0 ? (
            prompts.map(prompt => (
              <PromptCard 
                key={prompt.id} 
                prompt={prompt}
                onEdit={() => router.push(`/prompts/${prompt.id}/edit`)}
                onTest={() => router.push(`/prompts/${prompt.id}/test`)}
                onDuplicate={() => duplicatePrompt(prompt.id)}
                onDelete={() => deletePrompt(prompt.id)}
              />
            ))
          ) : (
            <div className="col-span-full text-center py-12">
              <div className="text-gray-500 text-lg mb-4">No prompts found</div>
              <Button 
                onClick={() => router.push('/prompts/create')}
                variant="outline"
              >
                Create Your First Prompt
              </Button>
            </div>
          )}
        </div>

        {/* Pagination */}
        {prompts.length > 0 && (
          <div className="mt-8 flex justify-center">
            {/* Add pagination component */}
          </div>
        )}
      </div>
    </Layout>
  )
}
```

### 2. Prompt Editor Component

```typescript
// components/prompts/PromptEditor.tsx
import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import CodeEditor from '../ui/CodeEditor'
import JsonEditor from '../ui/JsonEditor'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'

interface PromptEditorProps {
  promptId?: string
  initialData?: any
  onSave: (data: any) => Promise<void>
  onTest?: (data: any) => void
}

export default function PromptEditor({ 
  promptId, 
  initialData, 
  onSave, 
  onTest 
}: PromptEditorProps) {
  const [agentConfigs, setAgentConfigs] = useState([])
  const [selectedAgentConfig, setSelectedAgentConfig] = useState(null)
  const [saving, setSaving] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: { errors, isDirty }
  } = useForm({
    defaultValues: initialData || {
      display_name: '',
      agent_type: '',
      template_key: '',
      baml_template: '',
      input_schema: {},
      output_schema: {},
      test_parameters: {},
      version: '1.0.0',
      status: 'draft'
    }
  })

  const selectedAgentType = watch('agent_type')

  useEffect(() => {
    fetchAgentConfigs()
  }, [])

  useEffect(() => {
    if (selectedAgentType) {
      const config = agentConfigs.find(c => c.agent_type === selectedAgentType)
      setSelectedAgentConfig(config)
      
      if (config && !promptId) { // Only set defaults for new prompts
        setValue('input_schema', config.input_parameters)
        setValue('test_parameters', config.default_test_params || {})
      }
    }
  }, [selectedAgentType, agentConfigs, promptId])

  const fetchAgentConfigs = async () => {
    try {
      const response = await fetch('/api/agents/configs')
      const data = await response.json()
      setAgentConfigs(data.docs || [])
    } catch (error) {
      console.error('Error fetching agent configs:', error)
    }
  }

  const handleSave = async (data: any) => {
    setSaving(true)
    try {
      await onSave(data)
    } finally {
      setSaving(false)
    }
  }

  const handleQuickTest = () => {
    const currentData = getValues()
    if (onTest) {
      onTest(currentData)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Main Editor */}
      <div className="lg:col-span-2 space-y-6">
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Basic Information</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Display Name</label>
              <input
                {...register('display_name', { required: 'Display name is required' })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Character Creator - Protagonist Template"
              />
              {errors.display_name && (
                <p className="text-red-500 text-sm mt-1">{errors.display_name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Agent Type</label>
              <select
                {...register('agent_type', { required: 'Agent type is required' })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select Agent Type</option>
                {agentConfigs.map(config => (
                  <option key={config.agent_type} value={config.agent_type}>
                    {config.display_name}
                  </option>
                ))}
              </select>
              {errors.agent_type && (
                <p className="text-red-500 text-sm mt-1">{errors.agent_type.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Template Key</label>
              <input
                {...register('template_key', { required: 'Template key is required' })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="character_creator_protagonist_v1"
              />
              {errors.template_key && (
                <p className="text-red-500 text-sm mt-1">{errors.template_key.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Status</label>
              <select
                {...register('status')}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="draft">Draft</option>
                <option value="testing">Testing</option>
                <option value="active">Active</option>
                <option value="deprecated">Deprecated</option>
              </select>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">BAML Template</h2>
            <div className="flex items-center space-x-2">
              <Badge variant="outline">Handlebars Syntax</Badge>
              {onTest && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={handleQuickTest}
                  disabled={!watch('baml_template') || !selectedAgentType}
                >
                  Quick Test
                </Button>
              )}
            </div>
          </div>
          
          <CodeEditor
            value={watch('baml_template')}
            onChange={(value) => setValue('baml_template', value, { shouldDirty: true })}
            language="handlebars"
            height="400px"
            placeholder="Enter your BAML template here..."
          />
          {errors.baml_template && (
            <p className="text-red-500 text-sm mt-2">{errors.baml_template.message}</p>
          )}
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Input Schema</h2>
            <JsonEditor
              value={watch('input_schema')}
              onChange={(value) => setValue('input_schema', value, { shouldDirty: true })}
              height="300px"
            />
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Output Schema</h2>
            <JsonEditor
              value={watch('output_schema')}
              onChange={(value) => setValue('output_schema', value, { shouldDirty: true })}
              height="300px"
            />
          </Card>
        </div>

        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Test Parameters</h2>
          <p className="text-sm text-gray-600 mb-4">
            Default parameters for quick testing this prompt
          </p>
          <JsonEditor
            value={watch('test_parameters')}
            onChange={(value) => setValue('test_parameters', value, { shouldDirty: true })}
            height="200px"
          />
        </Card>
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        {/* Agent Info */}
        {selectedAgentConfig && (
          <Card className="p-6">
            <h3 className="font-semibold mb-3">Agent Information</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium">Type:</span> {selectedAgentConfig.display_name}
              </div>
              <div>
                <span className="font-medium">Output Types:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selectedAgentConfig.output_types?.map(type => (
                    <Badge key={type} variant="secondary" size="sm">
                      {type}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <span className="font-medium">Testing:</span>
                <Badge 
                  variant={selectedAgentConfig.testing_enabled ? "success" : "warning"}
                  size="sm"
                  className="ml-1"
                >
                  {selectedAgentConfig.testing_enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              {selectedAgentConfig.processing_time_estimate && (
                <div>
                  <span className="font-medium">Est. Time:</span> {selectedAgentConfig.processing_time_estimate}s
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Actions */}
        <Card className="p-6">
          <h3 className="font-semibold mb-4">Actions</h3>
          <div className="space-y-3">
            <Button
              onClick={handleSubmit(handleSave)}
              disabled={saving || !isDirty}
              className="w-full"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
            
            {onTest && (
              <Button
                variant="outline"
                onClick={handleQuickTest}
                disabled={!watch('baml_template') || !selectedAgentType}
                className="w-full"
              >
                Open Test Studio
              </Button>
            )}
            
            <Button
              variant="outline"
              onClick={() => window.history.back()}
              className="w-full"
            >
              Cancel
            </Button>
          </div>
        </Card>

        {/* Version History */}
        {promptId && (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Version History</h3>
            <div className="text-sm text-gray-600">
              Current: v{watch('version')}
            </div>
            <Button variant="outline" size="sm" className="mt-2">
              View History
            </Button>
          </Card>
        )}
      </div>
    </div>
  )
}
```

### 3. Test Studio Component

```typescript
// components/prompts/TestStudio.tsx
import { useState, useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs'
import DynamicForm from '../ui/DynamicForm'
import ResultViewer from './ResultViewer'

interface TestStudioProps {
  prompt: any
  agentConfig: any
  onRunTest: (params: any) => Promise<string> // Returns test result ID
}

export default function TestStudio({ prompt, agentConfig, onRunTest }: TestStudioProps) {
  const [testRunning, setTestRunning] = useState(false)
  const [currentTestId, setCurrentTestId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<any>(null)
  const [testHistory, setTestHistory] = useState([])
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const {
    handleSubmit,
    control,
    reset,
    getValues,
    formState: { isValid }
  } = useForm({
    defaultValues: prompt.test_parameters || agentConfig.default_test_params || {}
  })

  useEffect(() => {
    fetchTestHistory()
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [prompt.id])

  useEffect(() => {
    if (currentTestId) {
      startPolling()
    } else {
      stopPolling()
    }
  }, [currentTestId])

  const fetchTestHistory = async () => {
    try {
      const response = await fetch(`/api/prompts/${prompt.id}/test-history?limit=5`)
      const data = await response.json()
      setTestHistory(data.docs || [])
    } catch (error) {
      console.error('Error fetching test history:', error)
    }
  }

  const handleRunTest = async (formData: any) => {
    setTestRunning(true)
    setTestResult(null)
    
    try {
      const testId = await onRunTest({
        ...formData,
        test_name: `Test ${new Date().toLocaleTimeString()}`
      })
      
      setCurrentTestId(testId)
    } catch (error) {
      console.error('Test submission error:', error)
      setTestRunning(false)
    }
  }

  const startPolling = () => {
    pollIntervalRef.current = setInterval(async () => {
      if (!currentTestId) return

      try {
        const response = await fetch(`/api/test-results/${currentTestId}`)
        const result = await response.json()
        
        if (result.status !== 'running') {
          setTestResult(result)
          setCurrentTestId(null)
          setTestRunning(false)
          fetchTestHistory() // Refresh history
        }
      } catch (error) {
        console.error('Error polling test result:', error)
      }
    }, 2000) // Poll every 2 seconds
  }

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  const loadTestResult = async (testId: string) => {
    try {
      const response = await fetch(`/api/test-results/${testId}`)
      const result = await response.json()
      setTestResult(result)
    } catch (error) {
      console.error('Error loading test result:', error)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-screen max-h-screen overflow-hidden">
      {/* Left Panel - Test Configuration */}
      <div className="flex flex-col h-full overflow-hidden">
        <Card className="p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Test Configuration</h2>
            <Badge variant="outline">
              {agentConfig.display_name}
            </Badge>
          </div>

          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <h4 className="font-medium mb-2">{prompt.display_name}</h4>
            <p className="text-sm text-gray-600">v{prompt.version}</p>
          </div>

          <form onSubmit={handleSubmit(handleRunTest)}>
            <DynamicForm
              schema={prompt.input_schema}
              control={control}
              disabled={testRunning}
            />

            <div className="flex items-center justify-between mt-6">
              <div className="flex items-center space-x-2">
                <Button
                  type="submit"
                  disabled={testRunning || !isValid}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {testRunning ? 'Running Test...' : 'Run Test'}
                </Button>
                
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => reset()}
                  disabled={testRunning}
                >
                  Reset
                </Button>
              </div>

              {agentConfig.processing_time_estimate && (
                <div className="text-sm text-gray-600">
                  Est. time: {agentConfig.processing_time_estimate}s
                </div>
              )}
            </div>
          </form>
        </Card>

        {/* Test History */}
        <Card className="p-6 flex-1 overflow-hidden">
          <h3 className="font-semibold mb-4">Recent Tests</h3>
          <div className="space-y-2 overflow-y-auto max-h-60">
            {testHistory.map(test => (
              <div
                key={test.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                onClick={() => loadTestResult(test.id)}
              >
                <div>
                  <div className="font-medium text-sm">{test.test_name}</div>
                  <div className="text-xs text-gray-600">
                    {new Date(test.createdAt).toLocaleString()}
                  </div>
                </div>
                <Badge
                  variant={
                    test.status === 'completed' ? 'success' :
                    test.status === 'failed' ? 'destructive' :
                    test.status === 'running' ? 'default' : 'secondary'
                  }
                  size="sm"
                >
                  {test.status}
                </Badge>
              </div>
            ))}
            
            {testHistory.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                No tests run yet
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Right Panel - Results */}
      <div className="flex flex-col h-full overflow-hidden">
        <Card className="p-6 flex-1 overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Test Results</h2>
            {testRunning && (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-sm text-gray-600">Processing...</span>
              </div>
            )}
          </div>

          {testResult ? (
            <Tabs defaultValue="result" className="h-full flex flex-col">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="result">Result</TabsTrigger>
                <TabsTrigger value="parameters">Parameters</TabsTrigger>
                <TabsTrigger value="performance">Performance</TabsTrigger>
                <TabsTrigger value="raw">Raw Data</TabsTrigger>
              </TabsList>

              <div className="flex-1 overflow-hidden mt-4">
                <TabsContent value="result" className="h-full overflow-y-auto">
                  <ResultViewer 
                    result={testResult} 
                    outputTypes={agentConfig.output_types}
                  />
                </TabsContent>

                <TabsContent value="parameters" className="h-full overflow-y-auto">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <pre className="text-sm overflow-x-auto">
                      {JSON.stringify(testResult.test_parameters, null, 2)}
                    </pre>
                  </div>
                </TabsContent>

                <TabsContent value="performance" className="h-full overflow-y-auto">
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="text-sm font-medium text-gray-600">Processing Time</div>
                        <div className="text-2xl font-bold">
                          {testResult.result?.processing_time || 0}s
                        </div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="text-sm font-medium text-gray-600">Tokens Used</div>
                        <div className="text-2xl font-bold">
                          {testResult.result?.tokens_used || 0}
                        </div>
                      </div>
                    </div>

                    {testResult.status === 'failed' && testResult.error_details && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <h4 className="font-medium text-red-800 mb-2">Error Details</h4>
                        <p className="text-red-700 text-sm mb-2">
                          {testResult.error_details.error_message}
                        </p>
                        {testResult.error_details.stack_trace && (
                          <pre className="text-xs text-red-600 bg-red-100 p-2 rounded overflow-x-auto">
                            {testResult.error_details.stack_trace}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="raw" className="h-full overflow-y-auto">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <pre className="text-sm overflow-x-auto">
                      {JSON.stringify(testResult, null, 2)}
                    </pre>
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              {testRunning ? (
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p>Running test...</p>
                  <p className="text-sm mt-2">This may take a few moments</p>
                </div>
              ) : (
                <div className="text-center">
                  <p>Configure parameters and run a test to see results</p>
                  <p className="text-sm mt-2">Or select a test from the history</p>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
```

### 4. Result Viewer Component

```typescript
// components/prompts/ResultViewer.tsx
import { useState } from 'react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'

interface ResultViewerProps {
  result: any
  outputTypes: string[]
}

export default function ResultViewer({ result, outputTypes }: ResultViewerProps) {
  const [selectedMedia, setSelectedMedia] = useState<any>(null)

  const renderOutput = () => {
    if (!result.result?.output_data) {
      return <div className="text-gray-500">No output data available</div>
    }

    const outputData = result.result.output_data

    // Handle different output types
    if (typeof outputData === 'string') {
      return (
        <div className="bg-gray-50 rounded-lg p-4">
          <pre className="whitespace-pre-wrap text-sm">{outputData}</pre>
        </div>
      )
    }

    if (typeof outputData === 'object') {
      return (
        <div className="space-y-4">
          {/* Structured data display */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium mb-2">Generated Data</h4>
            <pre className="text-sm overflow-x-auto">
              {JSON.stringify(outputData, null, 2)}
            </pre>
          </div>

          {/* Character-specific display */}
          {outputData.name && (
            <Card className="p-4">
              <h3 className="font-semibold text-lg mb-2">{outputData.name}</h3>
              {outputData.role && (
                <Badge className="mb-3">{outputData.role}</Badge>
              )}
              
              <div className="space-y-3">
                {outputData.personality && (
                  <div>
                    <h4 className="font-medium text-sm text-gray-600">Personality</h4>
                    <p className="text-sm">{outputData.personality}</p>
                  </div>
                )}
                
                {outputData.appearance && (
                  <div>
                    <h4 className="font-medium text-sm text-gray-600">Appearance</h4>
                    <p className="text-sm">{outputData.appearance}</p>
                  </div>
                )}
                
                {outputData.background && (
                  <div>
                    <h4 className="font-medium text-sm text-gray-600">Background</h4>
                    <p className="text-sm">{outputData.background}</p>
                  </div>
                )}

                {outputData.motivation && (
                  <div>
                    <h4 className="font-medium text-sm text-gray-600">Motivation</h4>
                    <p className="text-sm">{outputData.motivation}</p>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      )
    }

    return (
      <div className="bg-gray-50 rounded-lg p-4">
        <pre className="text-sm">{String(outputData)}</pre>
      </div>
    )
  }

  const renderMedia = () => {
    if (!result.result?.generated_media || result.result.generated_media.length === 0) {
      return null
    }

    return (
      <div className="mt-6">
        <h4 className="font-medium mb-3">Generated Media</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {result.result.generated_media.map((media: any, index: number) => (
            <div 
              key={media.id || index}
              className="border rounded-lg p-2 cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => setSelectedMedia(media)}
            >
              {media.url && (
                <>
                  {media.mediaType === 'image' && (
                    <img 
                      src={media.url} 
                      alt={media.description || 'Generated image'}
                      className="w-full h-32 object-cover rounded"
                    />
                  )}
                  
                  {media.mediaType === 'video' && (
                    <video 
                      src={media.url}
                      className="w-full h-32 object-cover rounded"
                      controls
                      preload="metadata"
                    />
                  )}
                  
                  {media.mediaType === 'audio' && (
                    <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
                      <audio controls className="w-full">
                        <source src={media.url} />
                      </audio>
                    </div>
                  )}
                </>
              )}
              
              <div className="mt-2">
                <Badge size="sm">{media.mediaType}</Badge>
                {media.description && (
                  <p className="text-xs text-gray-600 mt-1 truncate">
                    {media.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Status */}
      <div className="flex items-center justify-between">
        <Badge
          variant={
            result.status === 'completed' ? 'success' :
            result.status === 'failed' ? 'destructive' :
            'default'
          }
        >
          {result.status}
        </Badge>
        
        <div className="text-sm text-gray-600">
          {new Date(result.createdAt).toLocaleString()}
        </div>
      </div>

      {/* Main Output */}
      {renderOutput()}
      
      {/* Generated Media */}
      {renderMedia()}

      {/* Media Modal */}
      {selectedMedia && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Media Preview</h3>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setSelectedMedia(null)}
              >
                Close
              </Button>
            </div>
            
            {selectedMedia.mediaType === 'image' && (
              <img 
                src={selectedMedia.url} 
                alt={selectedMedia.description}
                className="max-w-full max-h-[70vh] object-contain"
              />
            )}
            
            {selectedMedia.mediaType === 'video' && (
              <video 
                src={selectedMedia.url}
                controls
                className="max-w-full max-h-[70vh]"
              />
            )}
            
            {selectedMedia.description && (
              <p className="mt-4 text-sm text-gray-600">
                {selectedMedia.description}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

## Test Project Setup

### Default Test Project Creation

```typescript
// scripts/setup-test-project.ts
import { getPayloadClient } from '../src/utils/getPayload'

export async function createTestProject() {
  const payload = await getPayloadClient()
  
  try {
    // Check if test project already exists
    const existing = await payload.find({
      collection: 'projects',
      where: {
        id: { equals: 'test_project' }
      }
    })

    if (existing.docs.length > 0) {
      console.log('Test project already exists')
      return existing.docs[0]
    }

    // Create test project
    const testProject = await payload.create({
      collection: 'projects',
      data: {
        id: 'test_project',
        title: 'Test Project (System)',
        description: 'Internal project for testing AI agent prompts',
        genre: 'drama',
        episodeCount: 1,
        targetAudience: 'adult',
        status: 'concept',
        createdBy: 'system',
        projectSettings: {
          aspectRatio: '16:9',
          episodeDuration: 5, // Short for testing
          qualityTier: 'draft'
        },
        progress: {
          currentPhase: 'story_development',
          completedSteps: [],
          overallProgress: 0
        }
      }
    })

    console.log('Test project created:', testProject.id)
    return testProject

  } catch (error) {
    console.error('Error creating test project:', error)
    throw error
  }
}

// Run this during app initialization
if (require.main === module) {
  createTestProject().catch(console.error)
}
```

## Enhanced Features

### 1. Prompt Comparison Tool

```typescript
// components/prompts/PromptComparison.tsx
export default function PromptComparison({ promptIds }: { promptIds: string[] }) {
  // Side-by-side comparison of multiple prompts
  // A/B test results comparison
  // Performance metrics comparison
}
```

### 2. Batch Testing

```typescript
// pages/api/prompts/batch-test.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Test multiple prompts with same parameters
  // Useful for A/B testing different versions
}
```

### 3. Prompt Analytics Dashboard

```typescript
// components/prompts/PromptAnalytics.tsx  
export default function PromptAnalytics() {
  // Success rates over time
  // Most used prompts
  // Performance trends
  // Agent utilization statistics
}
```

This comprehensive prompt management and testing system transforms your auto-movie app into a powerful prompt engineering IDE, enabling creative teams to rapidly iterate on AI agent behaviors with immediate visual feedback and robust testing capabilities.