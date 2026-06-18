import { motion } from 'framer-motion'

/**
 * StaggerContainer + StaggerItem — parent/child stagger animations for lists.
 *
 * The container defines the stagger timing; each item animates in with a
 * delay based on its position. This creates the "cascade" effect Apple
 * uses in Settings lists, Mail inbox, etc.
 *
 * Usage:
 *   <StaggerContainer>
 *     {items.map(item => (
 *       <StaggerItem key={item.id}>
 *         <Card>...</Card>
 *       </StaggerItem>
 *     ))}
 *   </StaggerContainer>
 */

const containerVariants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.06,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 280,
      damping: 24,
    },
  },
}

export function StaggerContainer({ children, className = '' }) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className={className}
    >
      {children}
    </motion.div>
  )
}

export function StaggerItem({ children, className = '' }) {
  return (
    <motion.div variants={itemVariants} className={className}>
      {children}
    </motion.div>
  )
}
