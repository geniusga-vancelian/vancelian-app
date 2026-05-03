import { SiteCommonModuleEditor } from '@/components/admin/SiteCommonModuleEditor'

export default function AdminCommonModulePage({ params }: { params: { id: string } }) {
  return <SiteCommonModuleEditor moduleId={params.id} />
}
