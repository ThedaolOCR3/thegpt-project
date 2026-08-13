import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ChevronDown,
  ChevronRight,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  SquarePen,
  User,
} from 'lucide-react';
import { useSidebar } from './SidebarContext';
import { useAuth } from '../Auth/AuthContext';
import { HistoryItem } from './HistoryItem';
import { getConversations, renameConversation, deleteConversation } from '../../api/conversations';
import type { Conversation } from '../../api/types';

type FilterMode = 'all' | 'category';

export function Sidebar() {
  const { collapsed, toggle } = useSidebar();
  const { isLoggedIn, userId } = useAuth();
  const navigate = useNavigate();
  const { conversationId } = useParams();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filter, setFilter] = useState<FilterMode>('all');
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  useEffect(() => {
    // conversationId가 바뀔 때마다 다시 불러온다 — 메인 화면에서 새 대화를 만들어
    // 이동해온 경우처럼, 사이드바 바깥에서 목록이 바뀐 경우를 반영하기 위함.
    getConversations().then(setConversations);
  }, [conversationId]);

  async function handleRename(id: string, title: string) {
    setConversations((current) => current.map((c) => (c.id === id ? { ...c, title, isTitleCustom: true } : c)));
    await renameConversation(id, title);
  }

  async function handleDelete(id: string) {
    setConversations((current) => current.filter((c) => c.id !== id));
    await deleteConversation(id);
    if (conversationId === id) navigate('/');
  }

  function toggleCategory(label: string) {
    setCollapsedCategories((current) => {
      const next = new Set(current);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  function goToProfile() {
    navigate(isLoggedIn ? '/mypage' : '/login');
  }

  if (collapsed) {
    return (
      <aside className="flex h-full w-14 shrink-0 flex-col items-center gap-3 border-r border-neutral-200 bg-neutral-50 py-3 dark:border-neutral-800 dark:bg-neutral-900">
        <button
          type="button"
          title="사이드바 펼치기"
          aria-label="사이드바 펼치기"
          onClick={toggle}
          className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-200 dark:text-neutral-400 dark:hover:bg-neutral-800"
        >
          <PanelLeftOpen size={18} />
        </button>
        <div className="text-blue-600 dark:text-blue-400">
          <MessageSquare size={20} />
        </div>
        <button
          type="button"
          title="새 채팅"
          aria-label="새 채팅"
          onClick={() => navigate('/')}
          className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-200 dark:text-neutral-400 dark:hover:bg-neutral-800"
        >
          <SquarePen size={18} />
        </button>
        <div className="mt-auto">
          <button
            type="button"
            title={isLoggedIn ? '마이페이지' : '로그인'}
            aria-label={isLoggedIn ? '마이페이지' : '로그인'}
            onClick={goToProfile}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-200 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
          >
            <User size={16} />
          </button>
        </div>
      </aside>
    );
  }

  const grouped =
    filter === 'category'
      ? groupByCategory(conversations)
      : [{ label: null, items: conversations }];

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-1.5">
          <span className="text-blue-600 dark:text-blue-400">
            <MessageSquare size={20} />
          </span>
          <span className="font-semibold text-neutral-800 dark:text-neutral-100">TheGPT</span>
        </div>
        <button
          type="button"
          title="사이드바 접기"
          aria-label="사이드바 접기"
          onClick={toggle}
          className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-600 dark:text-neutral-500 dark:hover:bg-neutral-800 dark:hover:text-neutral-300"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      <div className="flex items-center justify-between px-4 pb-3">
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              filter === 'all'
                ? 'bg-white text-neutral-800 shadow-sm dark:bg-neutral-700 dark:text-neutral-50'
                : 'text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200'
            }`}
          >
            전체
          </button>
          <button
            type="button"
            onClick={() => setFilter('category')}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              filter === 'category'
                ? 'bg-white text-neutral-800 shadow-sm dark:bg-neutral-700 dark:text-neutral-50'
                : 'text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200'
            }`}
          >
            진료과별
          </button>
        </div>
        <button
          type="button"
          title="새 채팅"
          aria-label="새 채팅"
          onClick={() => navigate('/')}
          className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-600 dark:text-neutral-500 dark:hover:bg-neutral-800 dark:hover:text-neutral-300"
        >
          <SquarePen size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        {grouped.map((group) => {
          const isCollapsed = group.label ? collapsedCategories.has(group.label) : false;
          return (
            <div key={group.label ?? 'all'} className="mb-2">
              {group.label && (
                <button
                  type="button"
                  onClick={() => toggleCategory(group.label!)}
                  className="flex w-full items-center gap-1 px-2 pb-1 pt-2 text-xs font-medium text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                >
                  {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                  {group.label}
                  <span className="text-neutral-300 dark:text-neutral-600">({group.items.length})</span>
                </button>
              )}
              {!isCollapsed && (
                <div className="flex flex-col gap-0.5">
                  {group.items.map((conversation) => (
                    <HistoryItem
                      key={conversation.id}
                      conversation={conversation}
                      active={conversation.id === conversationId}
                      onSelect={() => navigate(`/chat/${conversation.id}`)}
                      onRename={(title) => handleRename(conversation.id, title)}
                      onDelete={() => handleDelete(conversation.id)}
                    />
                  ))}
                  {group.items.length === 0 && (
                    <p className="px-2 py-1 text-xs text-neutral-400 dark:text-neutral-600">대화 내역이 없습니다.</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button
        type="button"
        title={isLoggedIn ? '마이페이지로 이동' : '로그인하러 가기'}
        onClick={goToProfile}
        className="flex items-center gap-2 border-t border-neutral-200 px-4 py-3 text-left hover:bg-neutral-100 dark:border-neutral-800 dark:hover:bg-neutral-800"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-200 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-300">
          <User size={16} />
        </span>
        <span className="text-sm text-neutral-700 dark:text-neutral-200">아이디: {userId}</span>
      </button>
    </aside>
  );
}

function groupByCategory(conversations: Conversation[]) {
  const categories = new Map<string, Conversation[]>();
  for (const conversation of conversations) {
    const key = conversation.category ?? '기타';
    if (!categories.has(key)) categories.set(key, []);
    categories.get(key)!.push(conversation);
  }
  return Array.from(categories.entries()).map(([label, items]) => ({ label, items }));
}
