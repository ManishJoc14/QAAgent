import Link from "next/link"

const SiteHeader = () => {
    return (
        <header className="z-[10] mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-8">
            <Link href="/" className="text-xl font-semibold tracking-tight">
                QA agent
            </Link>
            <nav className="flex items-center gap-6 text-sm">
                <Link href="/qa" className="font-medium text-surface-fg">
                    try now
                </Link>
            </nav>
        </header>
    )
}

export default SiteHeader