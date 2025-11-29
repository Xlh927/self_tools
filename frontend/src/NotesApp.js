import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom/client';
import BalloonNote from './components/BalloonNote.js';

const { createElement: e } = React;

const CATEGORIES = [
    { id: 'linux', name: 'Linux', icon: '🐧', color: '#ffa500' },
    { id: 'python', name: 'Python', icon: '🐍', color: '#3776ab' },
    { id: 'git', name: 'Git', icon: '📦', color: '#f05032' },
    { id: 'docker', name: 'Docker', icon: '🐳', color: '#2496ed' },
    { id: 'database', name: 'Database', icon: '🗄️', color: '#336791' },
    { id: 'network', name: 'Network', icon: '🌐', color: '#00d4ff' },
    { id: 'general', name: 'General', icon: '📝', color: '#667eea' },
];

function NotesApp() {
    const [notes, setNotes] = useState([]);
    const [filteredNotes, setFilteredNotes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [currentTheme, setCurrentTheme] = useState(() => {
        return localStorage.getItem('app-theme') || 'default';
    });

    // Filters
    const [searchQuery, setSearchQuery] = useState('');

    // Form state
    const [showForm, setShowForm] = useState(false);
    const [editingNote, setEditingNote] = useState(null);
    const [formData, setFormData] = useState({
        title: '',
        category: 'general',
        command: '',
        description: '',
        tags: []
    });

    // Container size for balloons
    const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
    const containerRef = useRef(null);

    // Apply theme
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('app-theme', currentTheme);
    }, [currentTheme]);

    // Update container size on resize
    useEffect(() => {
        const updateSize = () => {
            if (containerRef.current) {
                setContainerSize({
                    width: containerRef.current.offsetWidth,
                    height: containerRef.current.offsetHeight
                });
            }
        };

        window.addEventListener('resize', updateSize);
        updateSize();

        return () => window.removeEventListener('resize', updateSize);
    }, []);

    // Load notes on mount
    useEffect(() => {
        fetchNotes();
    }, []);

    // Filter notes
    useEffect(() => {
        let filtered = notes;

        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(n =>
                n.title.toLowerCase().includes(query) ||
                n.command.toLowerCase().includes(query) ||
                n.description.toLowerCase().includes(query)
            );
        }

        setFilteredNotes(filtered);
    }, [notes, searchQuery]);

    const fetchNotes = async () => {
        try {
            const response = await fetch('/api/notes');
            const data = await response.json();
            if (data.success) {
                setNotes(data.notes);
            }
        } catch (error) {
            console.error('Failed to fetch notes:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateNote = async () => {
        try {
            const response = await fetch('/api/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            const data = await response.json();
            if (data.success) {
                fetchNotes();
                resetForm();
            }
        } catch (error) {
            console.error('Failed to create note:', error);
        }
    };

    const handleUpdateNote = async () => {
        try {
            const response = await fetch(`/api/notes/${editingNote.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            const data = await response.json();
            if (data.success) {
                fetchNotes();
                resetForm();
            }
        } catch (error) {
            console.error('Failed to update note:', error);
        }
    };

    const handleDeleteNote = async (noteId) => {
        if (!confirm('确定要删除这条命令吗？')) return;

        try {
            const response = await fetch(`/api/notes/${noteId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            if (data.success) {
                fetchNotes();
                resetForm(); // Close modal if open
            }
        } catch (error) {
            console.error('Failed to delete note:', error);
        }
    };

    const openForm = (note = null) => {
        if (note) {
            setEditingNote(note);
            setFormData({
                title: note.title,
                category: note.category,
                command: note.command,
                description: note.description || '',
                tags: note.tags || []
            });
        } else {
            setEditingNote(null);
            setFormData({
                title: '',
                category: 'general',
                command: '',
                description: '',
                tags: []
            });
        }
        setShowForm(true);
    };

    const resetForm = () => {
        setShowForm(false);
        setEditingNote(null);
        setFormData({
            title: '',
            category: 'general',
            command: '',
            description: '',
            tags: []
        });
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text).then(() => {
            alert('已复制到剪贴板！');
        });
    };

    return e('div', {
        style: {
            height: '100vh',
            width: '100vw',
            background: 'var(--bg-primary)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            position: 'relative'
        }
    },
        // Header (Minimalist)
        e('header', {
            style: {
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                zIndex: 100,
                padding: 'var(--spacing-md)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                pointerEvents: 'none' // Let clicks pass through to balloons
            }
        },
            // Left: Home & Title
            e('div', { style: { pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: '1rem' } },
                e('a', {
                    href: '/',
                    className: 'glass-card',
                    style: {
                        padding: '0.5rem 1rem',
                        textDecoration: 'none',
                        color: 'var(--text-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        borderRadius: 'var(--radius-full)'
                    }
                }, '🏠 主页'),
                e('h1', {
                    style: {
                        margin: 0,
                        fontSize: '1.2rem',
                        color: 'var(--text-secondary)',
                        textShadow: '0 2px 4px rgba(0,0,0,0.1)'
                    }
                }, 'Command Balloons')
            ),

            // Right: Theme Switcher
            e('div', {
                className: 'glass-card',
                style: {
                    pointerEvents: 'auto',
                    padding: '0.3rem',
                    display: 'flex',
                    gap: '0.3rem',
                    borderRadius: 'var(--radius-full)'
                }
            },
                [
                    { id: 'default', icon: '💎' },
                    { id: 'pornhub', icon: '🟠' },
                    { id: 'douyin', icon: '🎵' },
                    { id: 'youtube', icon: '📺' }
                ].map(theme =>
                    e('button', {
                        key: theme.id,
                        onClick: () => setCurrentTheme(theme.id),
                        style: {
                            padding: '0.3rem 0.5rem',
                            background: currentTheme === theme.id ? 'var(--gradient-primary)' : 'transparent',
                            color: currentTheme === theme.id ? 'white' : 'var(--text-secondary)',
                            border: 'none',
                            borderRadius: 'var(--radius-full)',
                            cursor: 'pointer',
                            fontSize: '0.9rem',
                            transition: 'all 0.2s'
                        }
                    }, theme.icon)
                )
            )
        ),

        // Main Balloon Container
        e('div', {
            ref: containerRef,
            style: {
                flex: 1,
                position: 'relative',
                overflow: 'hidden',
                cursor: 'grab'
            }
        },
            loading ? e('div', {
                style: {
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    color: 'var(--text-secondary)'
                }
            }, 'Loading balloons...') :
                filteredNotes.map(note => {
                    const category = CATEGORIES.find(c => c.id === note.category) || CATEGORIES.find(c => c.id === 'general');
                    return e(BalloonNote, {
                        key: note.id,
                        note,
                        category,
                        containerSize,
                        onClick: openForm
                    });
                })
        ),

        // Bottom Controls (Floating Bar)
        e('div', {
            style: {
                position: 'absolute',
                bottom: '2rem',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: 100,
                display: 'flex',
                gap: '1rem',
                alignItems: 'center'
            }
        },
            // Search Bar
            e('div', {
                className: 'glass-card',
                style: {
                    padding: '0.5rem 1rem',
                    borderRadius: 'var(--radius-full)',
                    display: 'flex',
                    alignItems: 'center',
                    width: '300px'
                }
            },
                e('span', { style: { marginRight: '0.5rem' } }, '🔍'),
                e('input', {
                    type: 'text',
                    placeholder: 'Search commands...',
                    value: searchQuery,
                    onChange: (e) => setSearchQuery(e.target.value),
                    style: {
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-primary)',
                        width: '100%',
                        outline: 'none',
                        fontSize: '1rem'
                    }
                })
            ),

            // Add Button
            e('button', {
                onClick: () => openForm(),
                className: 'btn btn-primary',
                style: {
                    width: '50px',
                    height: '50px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    boxShadow: '0 4px 15px rgba(0,0,0,0.2)'
                }
            }, '➕')
        ),

        // Form Modal (Expanded View)
        showForm && e(NoteFormModal, {
            formData,
            setFormData,
            categories: CATEGORIES,
            isEditing: !!editingNote,
            onClose: resetForm,
            onSubmit: editingNote ? handleUpdateNote : handleCreateNote,
            onDelete: editingNote ? () => handleDeleteNote(editingNote.id) : null,
            onCopy: editingNote ? () => copyToClipboard(editingNote.command) : null
        })
    );
}

// NoteFormModal Component (Enhanced for Balloon UI)
function NoteFormModal({ formData, setFormData, categories, isEditing, onClose, onSubmit, onDelete, onCopy }) {
    return e('div', {
        style: {
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: 'var(--spacing-xl)'
        },
        onClick: onClose
    },
        e('div', {
            className: 'glass-card animate-fade-in-up',
            style: {
                maxWidth: '600px',
                width: '100%',
                maxHeight: '90vh',
                overflowY: 'auto',
                padding: 'var(--spacing-xl)',
                position: 'relative'
            },
            onClick: (e) => e.stopPropagation()
        },
            // Header
            e('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' } },
                e('h2', {
                    style: {
                        margin: 0,
                        fontSize: '1.5rem',
                        color: 'var(--text-primary)'
                    }
                }, isEditing ? '🎈 Command Details' : '🎈 New Balloon'),

                // Action Buttons for Edit Mode
                isEditing && e('div', { style: { display: 'flex', gap: '0.5rem' } },
                    e('button', {
                        onClick: onCopy,
                        className: 'btn-ghost',
                        title: 'Copy Command'
                    }, '📋'),
                    e('button', {
                        onClick: onDelete,
                        className: 'btn-ghost',
                        style: { color: 'var(--accent-red)' },
                        title: 'Pop Balloon'
                    }, '🗑️')
                )
            ),

            // Title
            e('div', { className: 'input-group' },
                e('label', { className: 'input-label' }, 'Title'),
                e('input', {
                    type: 'text',
                    className: 'input-field',
                    placeholder: 'e.g., Find large files',
                    value: formData.title,
                    onChange: (e) => setFormData({ ...formData, title: e.target.value })
                })
            ),

            // Category
            e('div', { className: 'input-group' },
                e('label', { className: 'input-label' }, 'Category (Color)'),
                e('div', { style: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' } },
                    categories.map(cat =>
                        e('button', {
                            key: cat.id,
                            onClick: () => setFormData({ ...formData, category: cat.id }),
                            style: {
                                padding: '0.5rem 1rem',
                                background: formData.category === cat.id ? cat.color : 'var(--bg-tertiary)',
                                color: formData.category === cat.id ? 'white' : 'var(--text-secondary)',
                                border: '1px solid var(--glass-border)',
                                borderRadius: 'var(--radius-full)',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                fontSize: '0.9rem'
                            }
                        }, `${cat.icon} ${cat.name}`)
                    )
                )
            ),

            // Command
            e('div', { className: 'input-group' },
                e('label', { className: 'input-label' }, 'Command'),
                e('div', { style: { position: 'relative' } },
                    e('textarea', {
                        className: 'input-field',
                        placeholder: 'e.g., find . -type f -size +100M',
                        value: formData.command,
                        onChange: (e) => setFormData({ ...formData, command: e.target.value }),
                        rows: 3,
                        style: { fontFamily: 'monospace', resize: 'vertical', paddingRight: '3rem' }
                    }),
                    isEditing && e('button', {
                        onClick: onCopy,
                        style: {
                            position: 'absolute',
                            top: '0.5rem',
                            right: '0.5rem',
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '1.2rem'
                        },
                        title: 'Copy'
                    }, '📋')
                )
            ),

            // Description
            e('div', { className: 'input-group' },
                e('label', { className: 'input-label' }, 'Description'),
                e('textarea', {
                    className: 'input-field',
                    placeholder: 'What does this command do?',
                    value: formData.description,
                    onChange: (e) => setFormData({ ...formData, description: e.target.value }),
                    rows: 2,
                    style: { resize: 'vertical' }
                })
            ),

            // Tags
            e('div', { className: 'input-group' },
                e('label', { className: 'input-label' }, 'Tags'),
                e('input', {
                    type: 'text',
                    className: 'input-field',
                    placeholder: 'comma, separated, tags',
                    value: Array.isArray(formData.tags) ? formData.tags.join(', ') : '',
                    onChange: (e) => setFormData({
                        ...formData,
                        tags: e.target.value.split(',').map(t => t.trim()).filter(Boolean)
                    })
                })
            ),

            // Footer Buttons
            e('div', {
                style: {
                    display: 'flex',
                    gap: 'var(--spacing-md)',
                    marginTop: 'var(--spacing-lg)'
                }
            },
                e('button', {
                    onClick: onClose,
                    className: 'btn-ghost',
                    style: { flex: 1 }
                }, 'Cancel'),
                e('button', {
                    onClick: onSubmit,
                    className: 'btn btn-primary',
                    style: { flex: 1 },
                    disabled: !formData.title || !formData.command
                }, isEditing ? 'Update Balloon' : 'Inflate Balloon')
            )
        )
    );
}

// Mount app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(e(NotesApp));
