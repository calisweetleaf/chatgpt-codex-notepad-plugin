import { requireChatGPTUser } from './chatgpt-auth';
export const dynamic = 'force-dynamic';
export default async function Home() {
  await requireChatGPTUser('/');
  return <iframe src="/operator" title="Cognitive Workspace research environment" style={{width:'100%',height:'100dvh',border:0,display:'block',background:'#101313'}} />;
}
