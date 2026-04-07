export default async function ContractPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;

    return (
        <main className="p-8">
            <h1 className="font-display text-3xl font-semibold">Contract Analysis</h1>
            <p className="mt-2 text-muted-foreground">Contract ID: {id}</p>
        </main>
    );
}