'use client'
import {
  LayoutDashboard, PlusCircle, UserRound,
  Image as ImageIcon, Link, UsersRound, FolderOpen, User,
  Sparkles, ChevronDown, Check, Search, Play, Eye, EyeOff,
  ArrowRight, ArrowLeft, SlidersHorizontal, Package,
  Bookmark, Download, RotateCcw, Plus, Trash2, X,
  UploadCloud, Pencil, PackageOpen, Hand, Menu, Minus,
  Video, MailCheck, Wand2, LayoutGrid, Sun, Moon, Star,
  AlertCircle, CircleCheck, CircleX, Lock, Shield, Save, Zap, ZapOff, Clock,
  Scissors, Upload, Type, ArrowUp, BookOpen, HelpCircle,
  Camera, ChevronRight, GripVertical, Home,
  TrendingUp, Film, ThumbsUp, ThumbsDown
} from 'lucide-react'
import type { LucideProps } from 'lucide-react'

const ICONS: Record<string, React.ComponentType<LucideProps>> = {
  'layout-dashboard': LayoutDashboard,
  'plus-circle': PlusCircle,
  'user-round': UserRound,
  'image': ImageIcon,
  'link': Link,
  'users-round': UsersRound,
  'folder-open': FolderOpen,
  'user': User,
  'sparkles': Sparkles,
  'chevron-down': ChevronDown,
  'chevron-right': ChevronRight,
  'grip-vertical': GripVertical,
  'camera': Camera,
  'check': Check,
  'search': Search,
  'play': Play,
  'eye': Eye,
  'eye-off': EyeOff,
  'arrow-right': ArrowRight,
  'arrow-left': ArrowLeft,
  'arrow-up': ArrowUp,
  'sliders-horizontal': SlidersHorizontal,
  'package': Package,
  'bookmark': Bookmark,
  'download': Download,
  'rotate-ccw': RotateCcw,
  'plus': Plus,
  'trash-2': Trash2,
  'x': X,
  'upload-cloud': UploadCloud,
  'pencil': Pencil,
  'package-open': PackageOpen,
  'hand': Hand,
  'menu': Menu,
  'minus': Minus,
  'video': Video,
  'mail-check': MailCheck,
  'wand-2': Wand2,
  'layout-grid': LayoutGrid,
  'sun': Sun,
  'moon': Moon,
  'star': Star,
  'alert-circle': AlertCircle,
  'circle-check': CircleCheck,
  'circle-x': CircleX,
  'lock': Lock,
  'shield': Shield,
  'save': Save,
  'zap': Zap,
  'zap-off': ZapOff,
  'clock': Clock,
  'scissors': Scissors,
  'upload': Upload,
  'type': Type,
  'book-open': BookOpen,
  'help-circle': HelpCircle,
  'home': Home,
  'trending-up': TrendingUp,
  'film': Film,
  'thumbs-up': ThumbsUp,
  'thumbs-down': ThumbsDown,
}

interface IconProps {
  name: string
  className?: string
  style?: React.CSSProperties
}

export default function Icon({ name, className, style }: IconProps) {
  const Component = ICONS[name]
  if (!Component) return null
  const s: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 'none',
    ...style,
  }
  return (
    <span className={className} style={s} aria-hidden="true">
      <Component style={{ width: '100%', height: '100%' }} strokeWidth={2} />
    </span>
  )
}
