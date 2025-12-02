import JobProgress from '@/components/jobs/JobProgress'

export default async function JobPage({
    params,
}: {
    params: Promise<{ id: string }>
}) {
    const { id } = await params

    return <JobProgress jobId={id} />
}
