/** @type {import('./$types').PageLoad} */
export function load({ params }) {
	return {
		series: [
			{
				name: 'State 1',
				data: [6356, 6218, 6156, 6526, 6356, 6256, 60056],
				color: '#1f77b4'
			},
			{
				name: 'State 2',
				data: [6556, 6725, 6424, 6356, 6586, 6756, 6616],
				color: '#ff7f0e'
			},
			{
				name: 'State 3',
				data: [6556, 6725, 6424, 6356, 6586, 6756, 6616],
				color: '#2ca02c'
			},
			{
				name: 'State 4',
				data: [6556, 6725, 6424, 6356, 6586, 6756, 6616],
				color: '#9467bd'
			},
			{
				name: 'State 5',
				data: [6556, 6725, 6424, 6356, 6586, 6756, 6616],
				color: '#8c564b'
			},
			{
				name: 'Revenue (previous period)',
				data: [6556, 6725, 6424, 6356, 6586, 6756, 6616],
				color: '#e377c2'
			},
		]
	};
}
