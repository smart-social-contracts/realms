export const mockOrganizations = [
  {
    id: '1',
    name: 'City Council',
    description: 'Municipal government organization',
    type: 'government',
    members: 12,
    status: 'active',
    created: '2020-01-01'
  },
  {
    id: '2',
    name: 'Business Association',
    description: 'Local business owners collective',
    type: 'business',
    members: 45,
    status: 'active',
    created: '2021-03-15'
  },
  {
    id: '3',
    name: 'Community Garden',
    description: 'Neighborhood gardening group',
    type: 'community',
    members: 28,
    status: 'active',
    created: '2022-05-20'
  }
];

export const mockTrafficData = {
  totalVisitors: 1247,
  uniqueVisitors: 892,
  pageViews: 3456,
  bounceRate: 0.34,
  avgSessionDuration: '4:32',
  topPages: [
    { path: '/dashboard', views: 456, percentage: 32 },
    { path: '/extensions', views: 234, percentage: 18 },
    { path: '/organizations', views: 189, percentage: 14 }
  ]
};
