export const ADMIN_USER_ID = 'admin-user'

export const DEMO_USERS = [
  {
    id: ADMIN_USER_ID,
    name: 'Aarav Patel',
    email: 'admin@findx.ai',
    password: 'admin123',
    role: 'Admin',
    department: 'Platform Security',
  },
  {
    id: 'hr-user',
    name: 'Meera Shah',
    email: 'hr@findx.ai',
    password: 'hr123',
    role: 'HR',
    department: 'People Operations',
  },
  {
    id: 'employee-user',
    name: 'Rohan Singh',
    email: 'employee@findx.ai',
    password: 'employee123',
    role: 'Employee',
    department: 'Product Design',
  },
]

export const VISIBILITY_OPTIONS = [
  { id: 'private', label: 'Private' },
  { id: 'hr', label: 'HR' },
  { id: 'employee', label: 'Employees' },
  { id: 'both', label: 'Both' },
]

export function getVisibilityLabel(scope) {
  return VISIBILITY_OPTIONS.find((option) => option.id === scope)?.label ?? 'Private'
}

export const ROLE_STYLES = {
  Admin: {
    badge: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100',
    dot: 'bg-emerald-400',
    soft: 'bg-emerald-500/10 text-emerald-100 border-emerald-400/20',
  },
  HR: {
    badge: 'border-fuchsia-400/20 bg-fuchsia-500/10 text-fuchsia-100',
    dot: 'bg-fuchsia-400',
    soft: 'bg-fuchsia-500/10 text-fuchsia-100 border-fuchsia-400/20',
  },
  Employee: {
    badge: 'border-blue-400/20 bg-blue-500/10 text-blue-100',
    dot: 'bg-blue-400',
    soft: 'bg-blue-500/10 text-blue-100 border-blue-400/20',
  },
}

export const SUGGESTED_QUERIES = {
  Employee: [
    'How many annual leaves do employees receive?',
    'What is the remote work reimbursement policy?',
    'Can I carry forward unused leave?',
  ],
  HR: [
    'Summarize the maternity leave eligibility rule.',
    'Which document explains leave approval workflow?',
    'How should HR process protected leave requests?',
  ],
  Admin: [
    'What are the access review requirements?',
    'Who can see the security documents?',
    'Which documents are restricted right now?',
  ],
}

export const INITIAL_DOCUMENTS = [
  {
    id: 'doc-1',
    name: 'HR_Policy.pdf',
    type: 'PDF',
    ownerId: 'hr-user',
    ownerName: 'Meera Shah',
    uploadedAt: 'Today',
    visibilityScope: 'both',
    summary: 'Leave, attendance, and baseline workforce rules.',
  },
  {
    id: 'doc-2',
    name: 'Leave_Guidelines.pdf',
    type: 'PDF',
    ownerId: 'hr-user',
    ownerName: 'Meera Shah',
    uploadedAt: 'Today',
    visibilityScope: 'both',
    summary: 'Leave request workflow and approval path.',
  },
  {
    id: 'doc-3',
    name: 'Remote_Work_Policy.pdf',
    type: 'PDF',
    ownerId: 'employee-user',
    ownerName: 'Rohan Singh',
    uploadedAt: 'Yesterday',
    visibilityScope: 'both',
    summary: 'Remote work eligibility and reimbursement support.',
  },
  {
    id: 'doc-4',
    name: 'Benefits_Handbook.pdf',
    type: 'PDF',
    ownerId: 'hr-user',
    ownerName: 'Meera Shah',
    uploadedAt: 'Yesterday',
    visibilityScope: 'hr',
    summary: 'Protected leave programs and benefits eligibility.',
  },
  {
    id: 'doc-5',
    name: 'HR_Operations.txt',
    type: 'TXT',
    ownerId: 'hr-user',
    ownerName: 'Meera Shah',
    uploadedAt: '2 days ago',
    visibilityScope: 'hr',
    summary: 'Internal HR review and approval notes.',
  },
  {
    id: 'doc-6',
    name: 'Security_Standard.pdf',
    type: 'PDF',
    ownerId: ADMIN_USER_ID,
    ownerName: 'Aarav Patel',
    uploadedAt: '2 days ago',
    visibilityScope: 'private',
    summary: 'Privileged access review and security governance requirements.',
  },
  {
    id: 'doc-7',
    name: 'Incident_Playbook.pdf',
    type: 'PDF',
    ownerId: ADMIN_USER_ID,
    ownerName: 'Aarav Patel',
    uploadedAt: '3 days ago',
    visibilityScope: 'private',
    summary: 'Incident escalation workflow for high-risk findings.',
  },
]

export const DOCUMENT_LIBRARY = {
  'HR_Policy.pdf': {
    section: 'Section 2.1 | Leave entitlement',
    content: [
      'The Human Resources Policy outlines baseline employee entitlements, approval routes, and escalation rules for all full-time team members.',
      'All employees are entitled to 12 days of annual leave during each calendar year.',
      'Unused leave may be carried forward only with HR approval and subject to operational coverage requirements.',
    ],
  },
  'Leave_Guidelines.pdf': {
    section: 'Page 1 | Leave request workflow',
    content: [
      'The leave guidelines document describes how leave is requested, approved, and recorded through the internal HR portal.',
      'Planned leave must be submitted through the HR portal and approved by the reporting manager.',
      'Emergency leave requests should be submitted within one business day of absence where possible.',
    ],
  },
  'Remote_Work_Policy.pdf': {
    section: 'Section 5.4 | Equipment reimbursement',
    content: [
      'The remote work policy defines what support the company offers to hybrid and fully remote employees.',
      'Employees approved for remote work may claim reimbursement for eligible home-office expenses on a quarterly basis.',
      'All claims are subject to documented receipts and finance approval thresholds.',
    ],
  },
  'Benefits_Handbook.pdf': {
    section: 'Section 4.2 | Protected leave benefits',
    content: [
      'Benefits policies explain eligibility requirements for parental and maternity programs available to employees.',
      'Maternity leave is available to employees who have completed the minimum service period defined by company policy.',
      'HR may request supporting documentation to validate eligibility and scheduling.',
    ],
  },
  'HR_Operations.txt': {
    section: 'Process note | Approval routing',
    content: [
      'Internal HR operations notes describe the review steps needed before a protected leave request is finalized.',
      'Requests are processed by HR after receiving supporting medical documentation and manager acknowledgement.',
      'Approved leave records are stored in the employee profile for compliance and payroll coordination.',
    ],
  },
  'Security_Standard.pdf': {
    section: 'Control 8.3 | Access review governance',
    content: [
      'Security standards define the organization mandatory control cadence for privileged systems and sensitive data.',
      'Quarterly access reviews are mandatory for privileged systems and must be retained for audit inspection.',
      'Review records should capture system owner sign-off, remediation items, and completion dates.',
    ],
  },
  'Incident_Playbook.pdf': {
    section: 'Escalation matrix | Security operations',
    content: [
      'The incident playbook documents response expectations for identified security risks and exceptions.',
      'High-risk findings must be escalated through the incident workflow within one business day.',
      'Security operations coordinates containment, evidence collection, and executive notification where needed.',
    ],
  },
  default: {
    section: 'Retrieved knowledge context',
    content: [
      'This preview simulates a retrieved source chunk in the explainability panel.',
      'Relevant passages are highlighted so users can trace answers back to allowed documents.',
    ],
  },
}

const RESPONSE_TEMPLATES = [
  {
    match: ['leave', 'annual', 'vacation', 'carry forward'],
    answer:
      'Employees are entitled to 12 annual leaves per calendar year, and carry-forward requests require HR approval when operational coverage allows.',
    explanation:
      'The answer combines the entitlement rule from the HR policy with the request workflow described in the leave guidelines.',
    sources: [
      {
        id: 'leave-policy',
        doc: 'HR_Policy.pdf',
        page: 3,
        confidence: '96%',
        text: 'All employees are entitled to 12 days of annual leave during each calendar year.',
      },
      {
        id: 'leave-guidelines',
        doc: 'Leave_Guidelines.pdf',
        page: 1,
        confidence: '91%',
        text: 'Planned leave must be submitted through the HR portal and approved by the reporting manager.',
      },
    ],
  },
  {
    match: ['remote', 'reimbursement', 'home office'],
    answer:
      'Remote employees can claim reimbursement for eligible home-office expenses, subject to documented receipts and finance approval thresholds.',
    explanation:
      'The system matched the remote work support section and returned the policy snippet most relevant to employee reimbursement.',
    sources: [
      {
        id: 'remote-policy',
        doc: 'Remote_Work_Policy.pdf',
        page: 4,
        confidence: '95%',
        text: 'Employees approved for remote work may claim reimbursement for eligible home-office expenses on a quarterly basis.',
      },
    ],
  },
  {
    match: ['maternity', 'parental', 'benefits', 'protected leave'],
    answer:
      'Eligible employees may access maternity leave benefits after meeting the minimum service requirement, and HR reviews the documentation before approval.',
    explanation:
      'This answer is derived from the benefits handbook and the HR operations notes that explain the internal review sequence.',
    sources: [
      {
        id: 'benefits-handbook',
        doc: 'Benefits_Handbook.pdf',
        page: 6,
        confidence: '94%',
        text: 'Maternity leave is available to employees who have completed the minimum service period defined by company policy.',
      },
      {
        id: 'hr-ops',
        doc: 'HR_Operations.txt',
        page: 2,
        confidence: '89%',
        text: 'Requests are processed by HR after receiving supporting medical documentation and manager acknowledgement.',
      },
    ],
  },
  {
    match: ['access', 'security', 'incident', 'retention', 'privileged'],
    answer:
      'Privileged systems require quarterly access reviews, and high-risk exceptions must be escalated through the incident workflow within one business day.',
    explanation:
      'The response joins the governance control from the security standard with the escalation step in the incident playbook.',
    sources: [
      {
        id: 'security-standard',
        doc: 'Security_Standard.pdf',
        page: 9,
        confidence: '97%',
        text: 'Quarterly access reviews are mandatory for privileged systems and must be retained for audit inspection.',
      },
      {
        id: 'incident-playbook',
        doc: 'Incident_Playbook.pdf',
        page: 5,
        confidence: '92%',
        text: 'High-risk findings must be escalated through the incident workflow within one business day.',
      },
    ],
  },
]

export function getDemoUser(email, password) {
  return (
    DEMO_USERS.find(
      (user) =>
        user.email.toLowerCase() === email.toLowerCase() && user.password === password,
    ) ?? null
  )
}

export function getDefaultUploadVisibility(user) {
  if (!user) {
    return 'private'
  }

  if (user.role === 'Admin') {
    return 'both'
  }

  return user.role === 'HR' ? 'hr' : 'employee'
}

export function normalizeVisibilityScope(scope) {
  return VISIBILITY_OPTIONS.some((option) => option.id === scope) ? scope : 'private'
}

export function createWelcomeMessage(user) {
  return {
    id: crypto.randomUUID(),
    type: 'assistant',
    kind: 'welcome',
    text: `Welcome ${user.name}. You are signed in to FindX as ${user.role}. Ask questions only across documents you can access.`,
    explanation:
      'FindX only answers from the files visible to your account. Admin can update visibility or remove any uploaded file.',
    suggested: true,
    sources: [],
    createdAt: new Date().toISOString(),
  }
}

export function createConversation(user) {
  return {
    id: crypto.randomUUID(),
    title: 'New chat',
    updatedAt: new Date().toISOString(),
    messages: [createWelcomeMessage(user)],
  }
}

export function getAccessibleDocuments(documents, user) {
  if (!user) {
    return []
  }

  if (user.role === 'Admin') {
    return documents
  }

  return documents.filter((document) => {
    if (document.ownerId === user.id) {
      return true
    }

    switch (document.visibilityScope) {
      case 'hr':
        return user.role === 'HR'
      case 'employee':
        return user.role === 'Employee'
      case 'both':
        return user.role === 'HR' || user.role === 'Employee'
      default:
        return false
    }
  })
}

export function buildMockResponse(query, user, documents) {
  const normalized = query.toLowerCase()
  const accessibleNames = new Set(getAccessibleDocuments(documents, user).map((doc) => doc.name))
  const template =
    RESPONSE_TEMPLATES.find((entry) =>
      entry.match.some((keyword) => normalized.includes(keyword)),
    ) ?? RESPONSE_TEMPLATES[0]

  const filteredSources = template.sources.filter((source) => accessibleNames.has(source.doc))

  if (!filteredSources.length) {
    return {
      id: crypto.randomUUID(),
      type: 'assistant',
      kind: 'response',
      text: `No accessible source was found for this ${user.role} account. Ask the file owner or admin to update visibility.`,
      explanation:
        'FindX checked the document set visible to your user account and did not find an allowed source chunk to cite for this answer.',
      sources: [],
      createdAt: new Date().toISOString(),
    }
  }

  return {
    id: crypto.randomUUID(),
    type: 'assistant',
    kind: 'response',
    text: template.answer,
    explanation: template.explanation,
    sources: filteredSources,
    createdAt: new Date().toISOString(),
  }
}

export function canDeleteDocument(document, user) {
  if (!user) {
    return false
  }

  return user.role === 'Admin'
}

export function canEditDocumentVisibility(document, user) {
  if (!user) {
    return false
  }

  return user.role === 'Admin'
}

export function formatConversationTime(value) {
  const date = new Date(value)
  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}
