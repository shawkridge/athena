import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { Sparkles, TrendingUp, Lightbulb, AlertCircle, MessageSquare, Send } from 'lucide-react'

interface Insight {
  id: string
  type: 'recommendation' | 'pattern' | 'alert' | 'opportunity'
  title: string
  description: string
  confidence: number
  actionable: boolean
  timestamp: string
}

const mockInsights: Insight[] = [
  {
    id: '1',
    type: 'pattern',
    title: 'New Pattern Detected: Error Handling Workflow',
    description: 'The system identified a recurring pattern in your code commits. You consistently implement try-catch blocks followed by logging. This could be extracted as a reusable procedure.',
    confidence: 94,
    actionable: true,
    timestamp: '2 minutes ago',
  },
  {
    id: '2',
    type: 'recommendation',
    title: 'Consolidation Opportunity',
    description: '87% consolidation complete. 3 new patterns ready for extraction. Running consolidation now would improve memory efficiency by ~12%.',
    confidence: 89,
    actionable: true,
    timestamp: '15 minutes ago',
  },
  {
    id: '3',
    type: 'opportunity',
    title: 'Learning Acceleration Available',
    description: 'Based on your recent work, 5 related procedures exist in semantic memory that could accelerate your current task by 40%.',
    confidence: 78,
    actionable: true,
    timestamp: '1 hour ago',
  },
  {
    id: '4',
    type: 'alert',
    title: 'Cognitive Load Approaching Threshold',
    description: 'Working memory is at 6/7 items. Consider completing or delegating 1-2 tasks to maintain optimal performance.',
    confidence: 92,
    actionable: false,
    timestamp: '2 hours ago',
  },
]

const getInsightIcon = (type: string) => {
  switch (type) {
    case 'pattern':
      return Sparkles
    case 'recommendation':
      return TrendingUp
    case 'opportunity':
      return Lightbulb
    case 'alert':
      return AlertCircle
    default:
      return Sparkles
  }
}

const getInsightColor = (type: string) => {
  switch (type) {
    case 'pattern':
      return 'text-purple-600 bg-purple-50 dark:bg-purple-950/30'
    case 'recommendation':
      return 'text-blue-600 bg-blue-50 dark:bg-blue-950/30'
    case 'opportunity':
      return 'text-green-600 bg-green-50 dark:bg-green-950/30'
    case 'alert':
      return 'text-orange-600 bg-orange-50 dark:bg-orange-950/30'
    default:
      return 'text-gray-600 bg-gray-50 dark:bg-gray-950/30'
  }
}

export function AIInsightsPanel() {
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{ role: 'user' | 'ai'; message: string }>>([
    {
      role: 'ai',
      message: "Hi! I'm your Athena AI assistant. I can help you understand your memory patterns, suggest optimizations, and answer questions about your work. What would you like to know?",
    },
  ])

  const handleSendMessage = () => {
    if (!chatMessage.trim()) return

    // Add user message
    setChatHistory((prev) => [...prev, { role: 'user', message: chatMessage }])

    // Simulate AI response (in production, this would call the backend)
    setTimeout(() => {
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'ai',
          message: `Based on your query about "${chatMessage}", I found 3 relevant patterns in your episodic memory. Would you like me to show you the details?`,
        },
      ])
    }, 1000)

    setChatMessage('')
  }

  return (
    <div className="space-y-6">
      {/* Proactive Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-600" />
            AI-Powered Insights
          </CardTitle>
          <CardDescription>
            Proactive recommendations based on your memory patterns and work activity
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mockInsights.map((insight) => {
            const Icon = getInsightIcon(insight.type)
            const colorClass = getInsightColor(insight.type)

            return (
              <div
                key={insight.id}
                className="group p-4 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-all hover:shadow-md"
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${colorClass}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-slate-900 dark:text-white">
                        {insight.title}
                      </h4>
                      <Badge variant="secondary" className="text-xs">
                        {insight.confidence}% confident
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                      {insight.description}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">{insight.timestamp}</span>
                      {insight.actionable && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          Take Action
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>

      <Separator />

      {/* Conversational Interface */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-blue-600" />
            Ask Athena
          </CardTitle>
          <CardDescription>
            Natural language queries about your memory, patterns, and tasks
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Chat History */}
          <div className="mb-4 space-y-3 max-h-96 overflow-y-auto">
            {chatHistory.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] p-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                  }`}
                >
                  <p className="text-sm">{msg.message}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <Input
              placeholder="Ask about patterns, tasks, or optimizations..."
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              className="flex-1"
            />
            <Button onClick={handleSendMessage} size="icon">
              <Send className="h-4 w-4" />
            </Button>
          </div>

          {/* Suggested Questions */}
          <div className="mt-4">
            <p className="text-xs text-slate-500 mb-2">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {[
                'What patterns did I work on today?',
                'Show me related tasks',
                'Optimize my memory',
                'What should I focus on?',
              ].map((suggestion, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => setChatMessage(suggestion)}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <Card className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/30 dark:to-blue-950/30 border-none">
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {mockInsights.length}
              </p>
              <p className="text-xs text-slate-600 dark:text-slate-400">Active Insights</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">94%</p>
              <p className="text-xs text-slate-600 dark:text-slate-400">Avg Confidence</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">3</p>
              <p className="text-xs text-slate-600 dark:text-slate-400">Ready to Act</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">12%</p>
              <p className="text-xs text-slate-600 dark:text-slate-400">Efficiency Gain</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
