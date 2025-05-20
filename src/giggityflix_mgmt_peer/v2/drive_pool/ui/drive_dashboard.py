# giggityflix_mgmt_peer/v2/drive_pool/ui/drive_dashboard.py
from typing import List
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..drive_detection.detection import get_all_physical_drives
from ..drive_detection.models import PhysicalDrive

# Create router
router = APIRouter(prefix="/drives", tags=["drives"])

# Templates
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def drive_dashboard(request: Request):
    """Render the drive dashboard page."""
    return templates.TemplateResponse(
        "drive_dashboard.html",
        {"request": request}
    )


@router.get("/api/drives")
async def get_drives():
    """API endpoint to get drive information."""
    drives = get_all_physical_drives()
    return {
        "drives": [_drive_to_dict(drive) for drive in drives]
    }


def _drive_to_dict(drive: PhysicalDrive) -> dict:
    """Convert a PhysicalDrive to a dictionary for API response."""
    return {
        "id": drive.id,
        "display_id": drive.get_drive_id(),
        "manufacturer": drive.manufacturer,
        "model": drive.model,
        "serial": drive.serial,
        "size": drive.get_formatted_size(),
        "size_bytes": drive.size_bytes,
        "partitions": drive.partitions,
        "filesystem_type": drive.filesystem_type
    }


def create_react_artifact():
    """Create a React artifact for the drive dashboard."""
    return """
import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, HardDrive, Database } from 'lucide-react';

// Neobrutalism styling
const styles = {
  container: 'p-6 bg-yellow-100 min-h-screen',
  header: 'text-5xl font-bold mb-8 bg-pink-500 text-white p-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.8)] border-4 border-black',
  subheader: 'text-3xl font-bold mb-6 mt-8',
  card: 'bg-white p-6 mb-6 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,0.8)] hover:translate-x-1 hover:translate-y-1 hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,0.8)] transition-all cursor-pointer',
  cardSelected: 'bg-green-200 p-6 mb-6 border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,0.8)] translate-x-1 translate-y-1',
  cardHeader: 'flex justify-between items-center',
  cardTitle: 'text-2xl font-bold',
  cardContent: 'mt-4',
  cardDetail: 'p-4 border-t-2 border-gray-200 mt-4',
  infoRow: 'grid grid-cols-2 gap-4 mb-2',
  infoLabel: 'font-bold',
  infoValue: 'text-gray-800',
  partitionList: 'mt-4 pl-4',
  partition: 'p-3 mb-2 bg-blue-100 border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,0.8)]',
  icon: 'h-6 w-6 inline-block mr-2',
  partitionIcon: 'h-5 w-5 inline-block mr-2',
  errorMessage: 'p-4 bg-red-100 border-2 border-red-500 text-red-700 shadow-[4px_4px_0px_0px_rgba(0,0,0,0.8)]',
  loadingIndicator: 'flex items-center justify-center p-10',
};

const DriveCard = ({ drive, isExpanded, toggleExpand }) => {
  return (
    <div className={isExpanded ? styles.cardSelected : styles.card} onClick={toggleExpand}>
      <div className={styles.cardHeader}>
        <h3 className={styles.cardTitle}>
          <HardDrive className={styles.icon} />
          {drive.model !== 'Unknown' ? drive.model : drive.id}
        </h3>
        {isExpanded ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
      </div>
      <div className={styles.cardContent}>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Size:</span>
          <span className={styles.infoValue}>{drive.size}</span>
        </div>

        {isExpanded && (
          <div className={styles.cardDetail}>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>ID:</span>
              <span className={styles.infoValue}>{drive.id}</span>
            </div>
            {drive.manufacturer !== 'Unknown' && (
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Manufacturer:</span>
                <span className={styles.infoValue}>{drive.manufacturer}</span>
              </div>
            )}
            {drive.serial !== 'Unknown' && (
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Serial:</span>
                <span className={styles.infoValue}>{drive.serial}</span>
              </div>
            )}
            {drive.filesystem_type !== 'Unknown' && (
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Filesystem:</span>
                <span className={styles.infoValue}>{drive.filesystem_type}</span>
              </div>
            )}

            {drive.partitions && drive.partitions.length > 0 && (
              <>
                <h4 className="font-bold mt-4 mb-2">Partitions:</h4>
                <div className={styles.partitionList}>
                  {drive.partitions.map((partition, index) => (
                    <div key={index} className={styles.partition}>
                      <Database className={styles.partitionIcon} />
                      {partition}
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const DriveDashboard = () => {
  const [drives, setDrives] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedDrives, setExpandedDrives] = useState({});

  useEffect(() => {
    const fetchDrives = async () => {
      try {
        setLoading(true);
        const response = await fetch('/drives/api/drives');
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        setDrives(data.drives);

        // Initialize expanded state
        const expandState = {};
        data.drives.forEach(drive => {
          expandState[drive.id] = false;
        });
        setExpandedDrives(expandState);

        setError(null);
      } catch (err) {
        setError(`Failed to load drive information: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    fetchDrives();
  }, []);

  const toggleExpand = (driveId) => {
    setExpandedDrives(prev => ({
      ...prev,
      [driveId]: !prev[driveId]
    }));
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <h1 className={styles.header}>Giggityflix Drive Dashboard</h1>
        <div className={styles.loadingIndicator}>
          <span className="text-2xl">Loading drive information...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.header}>Giggityflix Drive Dashboard</h1>

      {error && (
        <div className={styles.errorMessage}>
          {error}
        </div>
      )}

      <h2 className={styles.subheader}>Physical Drives</h2>
      {drives.length === 0 ? (
        <div className="p-4 bg-gray-100 border-2 border-gray-300">
          No physical drives detected.
        </div>
      ) : (
        drives.map(drive => (
          <DriveCard 
            key={drive.id}
            drive={drive}
            isExpanded={expandedDrives[drive.id]}
            toggleExpand={() => toggleExpand(drive.id)}
          />
        ))
      )}
    </div>
  );
};

export default DriveDashboard;
"""