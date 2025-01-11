import TaskStatusModal from './TaskStatusModal';

export default function Navbar() {
  return (
    <nav className="border-b">
      <div className="flex h-16 items-center px-4">
        {/* ... other navbar items ... */}
        <div className="ml-auto flex items-center space-x-4">
          <TaskStatusModal />
          {/* ... other navbar items ... */}
        </div>
      </div>
    </nav>
  );
} 